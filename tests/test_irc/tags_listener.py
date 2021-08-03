import asyncio
import os
from dataclasses import dataclass
from itertools import combinations
from time import time
from typing import Iterable, Dict, List, Optional, AsyncIterator, Set
import asyncpg

from ttv.irc import Client, IRCMessage, ChannelMessage
from ttv.api import Api


class IRCListener(Client):
    def __init__(
            self,
            token: str,
            login: str,
            *,
            should_restart: bool = True,
            whisper_agent: str = None
    ):
        super().__init__(token, login, should_restart=should_restart, whisper_agent=whisper_agent)
        self.start_time = 0

    async def start(
            self,
            channels: Iterable[str]
    ) -> AsyncIterator[IRCMessage]:
        await self._first_log_in_irc()
        await self.join_channels(channels)
        # start main listener
        self.is_running = True
        self.start_time = time()
        async for irc_msg in self._read_websocket():
            yield irc_msg
        self.is_running = False


if __name__ == '__main__':
    DB_USER = os.environ['DB_USER']
    DB_PASS = os.environ['DB_PASS']
    DB_NAME = os.environ['DB_NAME']
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    IRC_TOKEN = os.environ['TTV_IRC_TOKEN']
    IRC_NICK = os.environ['TTV_IRC_NICK']
    CHNLS_COUNT = int(os.getenv('TTV_IRC_CHANNEL_COUNT', 50))
    API_TOKEN = os.environ['TTV_API_TOKEN']

    loop = asyncio.get_event_loop()
    db_pool = loop.run_until_complete(
        asyncpg.create_pool(user=DB_USER, password=DB_PASS, database=DB_NAME, host=DB_HOST)
    )
    local_db_copy: Dict[str, Dict[int, List[Dict[str, List[str]]]]] = {}


    async def create_tables():
        await db_pool.execute(
            'CREATE TABLE IF NOT EXISTS public.keys ( '
            'id smallint NOT NULL DEFAULT nextval(\'tags_keys_id_seq\'::regclass), '
            'command character varying COLLATE pg_catalog."default" NOT NULL, '
            'keys character varying[] COLLATE pg_catalog."default" NOT NULL, '
            'count integer NOT NULL DEFAULT 1, '
            'CONSTRAINT tags_keys_command_keys_key UNIQUE (command, keys) '
            ')'
        )
        await db_pool.execute(
            'CREATE TABLE IF NOT EXISTS public."values" ('
            '    id smallint NOT NULL DEFAULT nextval(\'tags_values_id_seq\'::regclass), '
            '    keys_id integer NOT NULL, '
            '    key character varying COLLATE pg_catalog."default" NOT NULL, '
            '    "values" character varying[] COLLATE pg_catalog."default", '
            '    can_be_empty boolean DEFAULT false, '
            '    CONSTRAINT tags_values_tags_keys_id_key_key UNIQUE (keys_id, key) '
            ')'
        )

    async def make_db_local_copy():
        all_unique_keys = await db_pool.fetch('SELECT id, command, keys FROM keys')
        for unique_keys in all_unique_keys:
            command = unique_keys['command']
            keys = unique_keys['keys']
            keys_id = unique_keys['id']
            tags = {}  # {key: [value, ...], ...}
            for key in keys:
                query = 'SELECT values, can_be_empty FROM values WHERE keys_id=$1 AND key=$2'
                all_values = await db_pool.fetchrow(query, keys_id, key)
                values: List[str] = all_values['values']
                if all_values['can_be_empty']:
                    values.insert(0, '')
                tags[key] = values
            tags_container = local_db_copy.setdefault(command, {})  # {keys_len: [{key: [value, ...]}, ...]}
            tags_list = tags_container.setdefault(len(keys), [])  # [{key: [value, ...]}, ...]
            tags_list.append(tags)

    async def check_irc_msg(irc_msg: IRCMessage):
        tags = make_values_list(irc_msg.tags)  # new dict
        if irc_msg.command not in local_db_copy:  # if new command
            local_db_copy[irc_msg.command] = {len(tags): [tags]}
            await save_new_keys(irc_msg)
        elif len(tags) not in local_db_copy[irc_msg.command]:  # if new len
            local_db_copy[irc_msg.command][len(tags)] = [tags]
            await save_new_keys(irc_msg)
        else:
            for saved_tags in local_db_copy[irc_msg.command][len(tags)]:
                if saved_tags.keys() == tags.keys():  # if known one
                    await increase_couner(irc_msg)
                    await check_values(irc_msg, saved_tags)
                    break
            else:  # if unknown one
                local_db_copy[irc_msg.command][len(tags)].append(tags)
                await save_new_keys(irc_msg)

    async def check_values(irc_msg: IRCMessage, saved_tags: Dict[str, List[str]]):
        for key in irc_msg.tags:
            if irc_msg.tags[key] not in saved_tags[key]:
                if len(saved_tags[key]) < 20:
                    saved_tags[key].append(irc_msg.tags[key])
                    await update_values(irc_msg, key, irc_msg.tags[key])
                elif irc_msg.tags[key] == '':
                    if '' not in saved_tags[key]:
                        saved_tags[key].insert(0, '')
                        await update_values(irc_msg, key, irc_msg.tags[key])

    def make_values_list(tags: Dict[str, Optional[str]]) -> Dict[str, List[str]]:
        new_tags: Dict[str, List[str]] = {}
        for key in tags:
            new_tags[key] = [tags[key]]
        return new_tags

    async def save_new_keys(irc_msg):
        keys = sorted(irc_msg.tags.keys())
        async with db_pool.acquire() as conn:
            print(f'{irc_msg.command} NEW KEYS {keys}')
            await conn.execute('INSERT INTO keys (command, keys) VALUES ($1, $2)', irc_msg.command, keys)
            keys_id = await conn.fetchval('SELECT id FROM keys WHERE command=$1 AND keys=$2', irc_msg.command, keys)
            await set_new_values(irc_msg, keys_id, conn)

    async def set_new_values(irc_msg, keys_id: int, conn):
        for key, value in irc_msg.tags.items():
            if value == '':
                print(f'{irc_msg.command}({keys_id}):{key} can be empty')
                await conn.execute(
                    'INSERT INTO values (keys_id, key, values, can_be_empty) VALUES ($1, $2, ARRAY[]::varchar[], TRUE)',
                    keys_id, key
                )
            else:
                print(f'{irc_msg.command}({keys_id}):{key} = {value}')
                await conn.execute(
                    'INSERT INTO values (keys_id, key, values) VALUES ($1, $2, ARRAY[$3]::varchar[])',
                    keys_id, key, value
                )

    async def update_values(irc_msg, key: str, value: str):
        keys = sorted(irc_msg.tags.keys())
        async with db_pool.acquire() as conn:
            keys_id = await db_pool.fetchval(
                'SELECT id FROM keys WHERE command=$1 AND keys=$2',
                irc_msg.command, keys
            )
            if value == '':
                print(f'{irc_msg.command}({keys_id}):{key} can be empty')
                await db_pool.execute(
                    'UPDATE values SET can_be_empty = TRUE WHERE keys_id=$1 AND key=$2',
                    keys_id, key
                )
            else:
                print(f'{irc_msg.command}({keys_id}):{key} = {value}')
                await db_pool.execute(
                    'UPDATE values SET values = array_append(values, $1) WHERE keys_id=$2 AND key=$3',
                    value, keys_id, key
                )

    async def increase_couner(irc_msg):
        keys = sorted(irc_msg.tags.keys())
        async with db_pool.acquire() as conn:
            await conn.execute(
                'UPDATE keys SET count = count + 1 WHERE command=$1 AND keys=$2',
                irc_msg.command, keys
            )

    async def start_listeners(listeners: List[IRCListener], channels_for_each: int):
        loop = asyncio.get_event_loop()
        api = await Api.create(API_TOKEN)
        count = len(listeners)
        chnls_count = count * channels_for_each
        top_channels = [json['user_login'] async for json in api.get_streams(chnls_count)]
        for i in range(count):
            start = i * channels_for_each
            end = start + channels_for_each
            loop.create_task(start_listener(listeners[i], top_channels[start:end]))
        print('LISTENERS HAVE BEEN STARTED')
        while True:
            await asyncio.sleep(30*60)
            top_channels = [json['user_login'] async for json in api.get_streams(chnls_count)]
            for i in range(count):
                await listeners[i].part_channels(listeners[i].joined_channel_logins)
                start = i * channels_for_each
                end = start + channels_for_each
                await listeners[i].join_channels(top_channels[start:end])
            print('CHANNEL UPDATED')


    async def start_listener(listener: IRCListener, channels: Iterable[str]):
        async for irc_msg in listener.start(channels):
            if irc_msg.command == 'USERNOTICE':
                irc_msg.command = irc_msg.tags['msg-id'].upper()
            await check_irc_msg(irc_msg)


    async def main():
        await create_tables()
        await make_db_local_copy()
        listeners = []
        bot = Client(IRC_TOKEN, IRC_NICK)

        @bot.event
        async def on_message(message: ChannelMessage):
            if message.channel.login == IRC_NICK:
                if message.author.login == IRC_NICK:
                    if message.content == '!write':
                        count = await save_tags_in_file()
                        await message.channel.send_message(str(count))
                    elif message.content.startswith('!smart'):
                        if 'privmsg' in message.content:
                            await save_privmsg_smart_log()
                        else:
                            await save_smart_log()
                    elif message.content.startswith('!stop'):
                        print('STOP has been requested')
                        for listener in listeners:
                            await listener._websocket.close()
                        await bot._websocket.close()

        run_mod = input('Run mode (listen or ttv_console, default: ttv_console): ')
        if run_mod == 'listen':
            listeners = [IRCListener(IRC_TOKEN, IRC_NICK) for _ in range(5)]
            await start_listeners(listeners, 50)
        elif run_mod == 'ttv_console':
            asyncio.get_event_loop().create_task(bot.start([IRC_NICK]))
        else:
            asyncio.get_event_loop().create_task(bot.start([IRC_NICK]))

    async def save_tags_in_file(file_name: str = 'tags.txt'):
        def write(text: str):
            file.write(text + '\n')

        def write_end(lvl: int):
            file.write('|--'*lvl + '\\' + '_'*10 + '\n')

        file = open(file_name, 'w', errors='ignore')

        async with db_pool.acquire() as conn:
            conn: asyncpg.connection.Connection
            commands_count = await conn.fetchval(
                'SELECT SUM(count) AS count FROM keys'
            )
            commands = [result['command'] for result in await conn.fetch(  # ORDER BY len, command, 0-length are last
                '''  
                SELECT command FROM (
                    SELECT DISTINCT ON (command) command, array_length(keys, 1) len
                    FROM keys 
                    ORDER BY command, len
                ) t
                ORDER BY len, command;
                '''
            )]
            write(f'All {len(commands)} names had {commands_count} instances\n')
            for command in commands:
                command_count = await conn.fetchval(
                    'SELECT SUM(count) AS count FROM keys WHERE command=$1', command
                )
                write(f'{command}: {command_count} instances')
                tags_types = await conn.fetch(
                    'SELECT id, keys, array_length(keys, 1) AS len, count '
                    'FROM keys WHERE command=$1 ORDER BY len, count  DESC',
                    command
                )
                base_keys = set(tags_types[0]['keys'])
                for tags_type in tags_types:
                    base_keys.intersection_update(set(tags_type['keys']))
                write(f'|--BASE {len(base_keys)}')
                for base_key in sorted(base_keys):
                    values_ = await conn.fetchrow(
                        'SELECT values.values, values.can_be_empty FROM keys '
                        'JOIN values ON keys.id=values.keys_id '
                        'WHERE keys.command=$1 AND values.key=$2 '
                        'ORDER BY array_length(keys.keys, 1) DESC '
                        'LIMIT 1',
                        command, base_key
                    )
                    values = values_['values']
                    values.insert(0, '') if values_['can_be_empty'] else None
                    write(f'|--|--{base_key}: {values}')
                write_end(lvl=1)
                sorted_tags_types = {}
                for tags in tags_types:
                    length = tags['len'] if tags['len'] is not None else 0
                    length -= len(base_keys)
                    sorted_tags_types.setdefault(length, []).append(tags)
                for length in sorted_tags_types:
                    if length == 0:
                        continue
                    types_count = len(sorted_tags_types[length])
                    count = tags_types[0]['count']
                    write(f'|-- +{length}: ' + (f'{count} intstances' if types_count == 1 else f'{types_count} types '))
                    for i, tags_type in enumerate(sorted_tags_types[length]):
                        count = tags_type['count']
                        if types_count != 1:
                            write(f'|--|--{length}.{i+1}: {count} intstances')
                        for key in sorted(set(tags_type['keys']) - base_keys):
                            values_ = await conn.fetchrow(
                                'SELECT values, can_be_empty FROM values WHERE keys_id=$1 AND key=$2',
                                tags_type['id'], key
                            )
                            values = values_['values']
                            values.insert(0, '') if values_['can_be_empty'] else None
                            write(f'|--|--|--{key}: {values}')
                        write_end(lvl=2)
                    write_end(lvl=1)
                write_end(lvl=0)
                write('')
        file.close()
        print('WROTE tags log')
        return commands_count

    async def save_smart_log(file_name: str = 'smart_tags.txt'):
        @dataclass
        class CommandTags:
            command: str
            base: set
            others: set

        file = open(file_name, 'w', errors='ignore')

        def write(text: str):
            file.write(text + '\n')

        def write_end(lvl: int):
            file.write('|--'*lvl + '\\' + '_'*10 + '\n')

        async with db_pool.acquire() as conn:
            conn: asyncpg.connection.Connection
            commands = [result['command'] for result in await conn.fetch(  # ORDER BY len, command, 0-length are last
                '''  
                SELECT command FROM (
                    SELECT DISTINCT ON (command) command, array_length(keys, 1) len
                    FROM keys 
                    ORDER BY command, len
                ) t 
                ORDER BY len, command;
                '''
            )]
            all_command_keys: List[CommandTags] = []
            for command in commands:
                not_base_tags: set = set()
                tags_types = await conn.fetch(
                    'SELECT keys FROM keys WHERE command=$1',
                    command
                )
                base_keys: set = set(tags_types[0]['keys'])
                all_keys: set = set()
                for tags_type in tags_types:
                    base_keys &= set(tags_type['keys'])
                    all_keys |= set(tags_type['keys'])
                all_command_keys.append(CommandTags(command, base_keys, all_keys - base_keys))
            for command_keys in all_command_keys:
                base_len = len(command_keys.base)
                not_base_len = len(command_keys.others)
                write(f'{command_keys.command}')
                if command_keys.base or command_keys.others:
                    write(f'|---BASE ({base_len}): {sorted(command_keys.base)}')
                    write(f'|---OTHER ({not_base_len}): {sorted(command_keys.others)}')
                write_end(0)
                write('')
            print('WROTE smart log')

    async def save_privmsg_smart_log(file_name: str = 'privmsg_log.txt'):
        @dataclass
        class KeysCombinations:
            combinations: Set[str]
            times_found: int

        file = open(file_name, 'w', errors='ignore')

        def write(text: str):
            file.write(text + '\n')

        def write_end(lvl: int):
            file.write('|--'*lvl + '\\' + '_'*10 + '\n')

        async with db_pool.acquire() as conn:
            types = await conn.fetch("SELECT keys FROM keys WHERE command='PRIVMSG'")
            base_keys: set = set(types[0]['keys'])
            all_keys: set = set()
            max_keys_len = 0
            keys_types: List[Set[str]] = []
            for type_ in types:
                keys_type = set(type_['keys'])
                base_keys.intersection_update(keys_type)
                all_keys.update(keys_type)
                keys_types.append(keys_type)
                max_keys_len = max(len(keys_type), max_keys_len)
            for keys_type in keys_types:
                keys_type.difference_update(base_keys)
            other_keys = all_keys - base_keys
            known_combinations: List[KeysCombinations] = []
            for keys_len in range(max_keys_len, 0, -1):  # for every possible length
                for keys_combination in combinations(other_keys, keys_len):  # for every possible combination
                    keys_combination: set = set(keys_combination)
                    times_found = 0
                    for keys_type in keys_types:  # for every known type
                        if keys_combination <= keys_type:  # if found as a subkeys
                            times_found += 1
                    if times_found < 2:
                        continue
                    for known_combination in known_combinations:  # for every know combination
                        if known_combination.combinations >= keys_combination:  # if known as a subcombination
                            if known_combination.times_found == times_found:  # and has been found same number of times
                                break
                    else:  # if new
                        known_combinations.append(KeysCombinations(keys_combination, times_found))
        last_lengh_print = 0
        for known_combination in known_combinations:
            length = len(known_combination.combinations)
            if last_lengh_print != length:
                write(f'LENGTH: {length}')
                last_lengh_print = length
            write(f'    {known_combination.combinations} {known_combination.times_found}')
        print('WROTE PRIVMSG log')


    asyncio.get_event_loop().create_task(main())
    asyncio.get_event_loop().run_forever()
