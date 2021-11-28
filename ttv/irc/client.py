import asyncio
from asyncio import iscoroutinefunction
from typing import Coroutine, Iterable, Tuple, Any, Awaitable, Callable, List, Optional, Dict

from .channel import Channel
from .channels_accumulators import ChannelsAccumulator
from .events import OnUserTimeout, OnChannelJoinError, OnNotice, OnMessageDelete, OnSendMessageError, OnUserBan, \
    OnClearChat
from .exceptions import *
from .irc_connections import TwitchIRCClient
from .irc_messages import TwitchIRCMsg
from .messages import ChannelMessage, Whisper
from .user_events import *
from .user_states import GlobalState, LocalState
from .users import ChannelUser, GlobalUser

__all__ = ('Client', )


class Client:

    def __init__(  # TODO: set all the accum bool variables True and review the anon script for them.
            self,
            token: str,
            login: str,
            *,
            keep_alive: bool = True
    ) -> None:
        self._irc_conn = TwitchIRCClient(login, token, keep_alive=keep_alive)
        # state
        self.global_state: Optional[GlobalState] = None
        # channels
        self._channels_by_id: Dict[str, Channel] = {}
        self._channels_by_login: Dict[str, Channel] = {}
        self._delayed_irc_msgs: Dict[str, List[TwitchIRCMsg]] = {}  # channel_login: [irc_msg, ...]
        # accumulation
        self._chnls_accum: ChannelsAccumulator = ChannelsAccumulator(
            channel_ready_callback=self._save_channel,
            irc_conn=self._irc_conn,
            is_anon=self.is_anon
        )

    @property
    def is_restarting(self) -> bool:
        return self._irc_conn.is_restarting

    @property
    def is_running(self) -> bool:
        return self._irc_conn.is_running

    @property
    def is_anon(self) -> bool:
        return self._irc_conn.is_anon

    def get_channel(
            self,
            login_or_id: str,
            default: Any = None
    ) -> Channel:
        """
        Returns :cls:`Channel`:
            1: by login if exists
            2: by id if exists
            3: default
        """
        try:
            return self._channels_by_login[login_or_id]
        except KeyError:
            return self._channels_by_id.get(login_or_id, default)

    def get_channel_by_id(
            self,
            channel_id: str,
            default: Any = None
    ) -> Channel:
        """Returns :cls:`Channel` by id if exists else - :arg:`default`"""
        return self._channels_by_id.get(channel_id, default)

    def get_channel_by_login(
            self,
            login: str,
            default: Any = None
    ) -> Channel:
        """Returns :cls:`Channel` by id if exists else - :arg:`default`"""
        return self._channels_by_login.get(login, default)

    def _get_prepared_channel(
            self,
            login: str
    ) -> Channel:
        """
        returns :class:`Channel` with given login if exists, else raises :exc:`ChannelNotAccumulated`

        Args:
            login :class:`str`: login of the channel that must be returned
        """
        try:
            return self._channels_by_login[login]
        except KeyError:
            raise ChannelNotAccumulated(login)

    def run(
            self,
            channels: Iterable[str]
    ) -> None:
        """
        Starts event listener.

        Args:
            channels Iterable[`str`] : Object with logins of channels to join

        Notes:
            Async version of the method is :meth:`start`
        """
        asyncio.get_event_loop().run_until_complete(
            self.start(channels)
        )

    async def start(
            self,
            channels: Iterable[str]
    ) -> None:
        """
        |Coroutine|
        Starts event listener.

        Notes:
            If you won't combine this with any other async code - you can use sync method 'self.run()'.

        Args:
            channels: (Iterable[str])
                Iterable object with logins of channel to join
        """
        global_state_msg = await self._irc_conn.connect()
        self.global_state = GlobalState(global_state_msg)
        self._call_event('on_ready')
        await self.join_channels(*channels)
        async for irc_msg in self._irc_conn:
            self._do_later(
                self._handle_command(irc_msg)  # protection from a shutdown caused by an exception
            )

    async def stop(self):  # TODO: script for case: self.is_running == False
        await self._irc_conn.stop()

    async def _handle_command(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        try:
            handler = self._COMMAND_HANDLERS[irc_msg.command]
        except KeyError:
            self._call_event('on_unknown_command', irc_msg)
        else:
            try:
                await handler(self, irc_msg)
            except ChannelNotAccumulated:
                await self._delay_irc_message(irc_msg)

    async def _handle_names_part(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        await self._chnls_accum.accumulate_part(irc_msg)

    async def _handle_names_end(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if irc_msg.channel in self._channels_by_login:
            await self._handle_names_update(irc_msg)
        else:
            await self._chnls_accum.accumulate_part(irc_msg)

    async def _handle_names_update(
            self,
            irc_msg: TwitchIRCMsg
    ):
        channel = self._channels_by_login[irc_msg.channel]
        before = channel.names
        after = channel.names = (await self._chnls_accum.abort_accumulations(irc_msg.channel)).names  # abort -> Parts
        self._call_event('on_names_update', channel, before, after)

    async def _handle_roomstate(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if irc_msg.channel in self._channels_by_login:
            await self._handle_channel_update(irc_msg)
        else:
            await self._chnls_accum.accumulate_part(irc_msg)

    async def _handle_channel_update(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        channel = self._channels_by_login[irc_msg.channel]
        if hasattr(self, 'on_channel_update'):  # Channel.copy() cost us much time
            before = channel.copy()
            channel.update_state(irc_msg)
            after = channel.copy()
            self._call_event('on_channel_update', before, after)
        else:
            channel.update_state(irc_msg)

    async def _handle_userstate(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        # prepare tags
        if 'user-login' not in irc_msg:
            irc_msg['user-login'] = self._irc_conn.login
        if 'user-id' not in irc_msg:
            irc_msg['user-id'] = self.global_state.id
        # if accumulated
        if irc_msg.channel in self._channels_by_login:
            await self._handle_userstate_update(irc_msg)
        else:
            await self._chnls_accum.accumulate_part(irc_msg)

    async def _handle_userstate_update(
            self,
            irc_msg: TwitchIRCMsg
    ):
        channel = self._channels_by_login[irc_msg.channel]
        before = channel.client_state
        after = channel.client_state = LocalState(irc_msg)
        self._call_event('on_client_state_update', channel, before, after)

    async def _handle_privmsg(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if hasattr(self, 'on_message'):
            channel = self._get_prepared_channel(irc_msg.channel)
            if 'user-login' not in irc_msg:
                irc_msg['user-login'] = irc_msg.nickname
            author = ChannelUser(irc_msg, channel, self._irc_conn)
            message = ChannelMessage(irc_msg, channel, author)
            self._call_event('on_message', message)

    async def _handle_whisper(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if hasattr(self, 'on_whisper'):
            if 'user-login' not in irc_msg:
                irc_msg['user-login'] = irc_msg.nickname
            author = GlobalUser(irc_msg, self._irc_conn)
            whisper = Whisper(irc_msg, author)
            self._call_event('on_whisper', whisper)

    async def _handle_join(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        self._call_event('on_user_join', channel, irc_msg.nickname)

    async def _handle_part(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        self._call_event('on_user_part', channel, irc_msg.nickname)

    async def _handle_notice(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        notice_id = irc_msg.msg_id
        if notice_id in ('msg_room_not_found', 'msg_channel_suspended'):
            await self._handle_channel_join_error(irc_msg)
        elif notice_id.startswith('msg'):
            # NOTE: 'msg_room_not_found' & 'msg_channel_suspended' are handled in the previous condition
            await self._handle_send_message_error(irc_msg)
        elif notice_id == 'cmds_available':
            await self._handle_cmds_available(irc_msg)
        elif notice_id in ('room_mods', 'no_mods'):
            await self._handle_mods(irc_msg)
        elif notice_id in ('vips_success', 'no_vips'):
            await self._handle_vips(irc_msg)
        else:
            channel = self._get_prepared_channel(irc_msg.channel)
            self._call_event('on_notice', OnNotice(channel, notice_id, irc_msg.trailing))
            
    async def _handle_channel_join_error(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        await self.part_channels(irc_msg.channel)
        reason = irc_msg.msg_id.removeprefix('msg_')
        self._call_event('on_channel_join_error', OnChannelJoinError(irc_msg.channel, reason, irc_msg.trailing))
            
    async def _handle_send_message_error(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        reason = irc_msg.msg_id.removeprefix('msg_')
        self._call_event('on_send_message_error', OnSendMessageError(channel, reason, irc_msg.trailing))

    async def _handle_cmds_available(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if (channel := self.get_channel(irc_msg.channel)) is None:
            await self._chnls_accum.accumulate_part(irc_msg)
        else:  # TODO: check msg-id = 'no_help'
            before = channel.commands
            raw_cmds = irc_msg.trailing.split(' More')[0]  # 'More help: https://help.twitch.tv/...'
            raw_cmds = raw_cmds.split(': ', 1)[1]  # 'Commands available to you in this room (...): '
            commands = tuple(raw_cmds.split(' '))
            after = channel.commands = commands
            self._call_event('on_commands_update', channel, before, after)

    async def _handle_mods(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if (channel := self.get_channel(irc_msg.channel)) is None:
            await self._chnls_accum.accumulate_part(irc_msg)
        else:
            before = channel.mods
            if irc_msg.msg_id == 'no_mods':
                mods = ()
            else:
                raw_mods = irc_msg.trailing.split(': ', 1)[1]  # remove 'The moderators of this channel are: '
                mods = tuple(raw_mods.split(', '))
            after = channel.mods = mods
            self._call_event('on_mods_update', channel, before, after)

    async def _handle_vips(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if (channel := self.get_channel(irc_msg.channel)) is None:
            await self._chnls_accum.accumulate_part(irc_msg)
        else:
            before = channel.vips
            if irc_msg.msg_id == 'no_vips':
                vips = ()
            else:
                raw_vips = irc_msg.trailing.split(': ', 1)[1]  # remove 'The VIPs of this channel are: '
                raw_vips = raw_vips.removesuffix('.')
                vips = tuple(raw_vips.split(', '))
            after = channel.vips = vips
            self._call_event('on_vips_update', channel, before, after)

    async def _handle_clearchat(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if irc_msg.trailing:  # trailing contains login of the user
            if 'ban-duration' in irc_msg:
                if hasattr(self, 'on_user_timeout'):
                    await self._handle_timeout(irc_msg)
            else:
                if hasattr(self, 'on_user_ban'):
                    await self._handle_ban(irc_msg)
        else:
            await self._handle_clear_chat(irc_msg)

    async def _handle_timeout(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        user_login = irc_msg.trailing
        timestamp = int(irc_msg.get('tmi-sent-ts', 0))
        user_id = irc_msg.get('target-user-id')
        message_id = irc_msg.get('target-msg-id')
        duration = int(irc_msg.get('ban-duration', 0))

        self._call_event(
            'on_user_timeout', OnUserTimeout(channel,  user_login, user_id, message_id, duration, timestamp)
        )

    async def _handle_ban(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        user_login = irc_msg.trailing
        timestamp = int(irc_msg.get('tmi-sent-ts', 0))
        user_id = irc_msg.get('target-user-id')
        message_id = irc_msg.get('target-msg-id')

        self._call_event('on_user_ban', OnUserBan(channel,  user_login, user_id, message_id, timestamp))

    async def _handle_clear_chat(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        timestamp = int(irc_msg.get('tmi-sent-ts', 0))
        self._call_event('on_clear_chat', OnClearChat(channel, timestamp))

    async def _handle_clearmsg(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if hasattr(self, 'on_message_delete'):
            channel = self._get_prepared_channel(irc_msg.channel)
            user_login = irc_msg.get('login')
            content = irc_msg.trailing
            message_id = irc_msg.get('target-msg-id')
            timestamp = int(irc_msg.get('tmi-sent-ts', 0))

            self._call_event(
                'on_message_delete',
                OnMessageDelete(channel, user_login, content, message_id, timestamp)
            )

    async def _handle_usernotice(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        channel = self._get_prepared_channel(irc_msg.channel)
        try:
            event_type = irc_msg.msg_id
            event_name, event_class = self._USER_EVENT_TYPES[event_type]
        # if unknown event
        except KeyError:
            self._call_event('on_unknown_user_event', irc_msg)
        # if known event
        else:
            # if has specified handler
            if hasattr(self, event_name):
                author = ChannelUser(irc_msg, channel, self._irc_conn)
                event = event_class(irc_msg, author, channel)
                self._call_event(event_name, event)
            # if has not specified handler
            elif hasattr(self, 'on_user_event'):
                author = ChannelUser(irc_msg, channel, self._irc_conn)
                event = event_class(irc_msg, author, channel)
                self._call_event('on_user_event', event)

    async def _handle_hosttarget(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if hasattr(self, 'on_host_start') or hasattr(self, 'on_host_stop'):
            host_login, viewers_count = irc_msg.trailing.split(' ', 1)
            if host_login == '-':
                await self._handle_host_start(irc_msg)
            else:
                await self._handle_host_stop(irc_msg)

    async def _handle_host_start(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if hasattr(self, 'on_host_start'):
            host_login, viewers_count = irc_msg.trailing.split(' ', 1)
            viewers_count = int(viewers_count) if (viewers_count != '-') else 0
            self._call_event('on_host_start', host_login, viewers_count)

    async def _handle_host_stop(
            self,
            irc_msg: TwitchIRCMsg
    ) -> None:
        if hasattr(self, 'on_host_stop'):
            _, viewers_count = irc_msg.trailing.split(' ', 1)
            viewers_count = int(viewers_count) if (viewers_count != '-') else None
            self._call_event('on_host_stop', viewers_count)

    async def _handle_globaluserstate(
            self,
            irc_msg: TwitchIRCMsg
    ):
        if 'user-login' not in irc_msg:
            irc_msg['user-login'] = self._irc_conn.login
        self.global_state = GlobalState(irc_msg)

    async def _handle_reconnect(
            self,
            _: TwitchIRCMsg
    ):
        self._do_later(self._irc_conn.restart())  # does not close connection if open

    def _save_channel(
            self,
            channel: Channel
    ) -> None:
        """
        1. Adds channel in `self._channels_by_id` and `self._channels_by_login`
        3. Handles delayed message for the channel
        2. Calls event handler `self.on_channel_join`

        Args:
            channel: `Channel`
                will be saved

        Returns:
            `None`
        """
        self._channels_by_id[channel.id] = channel
        self._channels_by_login[channel.login] = channel
        # handle delayed irc_messages
        delayed_irc_messages = self._delayed_irc_msgs.pop(channel.login, ())
        for delayed_irc_message in delayed_irc_messages:
            self._do_later(
                self._handle_command(delayed_irc_message)
            )
        self._call_event('on_channel_join', channel)

    async def _send(
            self,
            irc_message: str
    ) -> None:
        """
        Sends irc message to twitch irc server.
        Handles :class:`ConnectionClosedError`: restarts if should

        Args:
            irc_message: `str`
                command to send

        Returns:
            `None`
        """
        await self._irc_conn.send(irc_message)

    async def send_msg(
            self,
            channel_login: str,
            content: str
    ) -> None:
        """
        Sends `content` into the channel with login equals `channel_login`

        Args:
            channel_login: `str`
                login of channel into which `content` should be sent.
            content: `str`
                content to send into the channel

        Returns:
            `None`
        """
        await self._irc_conn.send_msg(channel_login, content)

    async def send_whisper(
            self,
            target: str,
            content: str
    ) -> None:
        """
        Sends whisper with `content` to the recipient with login equals `recipient_login`

        Args:
            target: `str`
                login of recipient
            content: `str`
                content to send

        Returns:
            `None`
        """
        await self._irc_conn.send_whisper(target, content)

    async def join_channels(self, *channels):
        await self._chnls_accum.start_accumulations(*channels)
        await self._irc_conn.join_channels(*channels)

    async def part_channels(self, *channels):
        await self._chnls_accum.abort_accumulations(*channels)
        await self._irc_conn.part_channels(*channels)
        for channel in channels:
            self._delayed_irc_msgs.pop(channel, None)

    async def _delay_irc_message(self, irc_msg: TwitchIRCMsg) -> None:
        """
        Delays `irc_msg`.
        Delayed message will be handled after the channel with `channel_login` is created

        Args:
            irc_msg: `TwitchIRCMsg`
                message to be delayed

        Returns:
            `None`
        """
        delayed_irc_messages = self._delayed_irc_msgs.setdefault(irc_msg.channel, [])
        if len(delayed_irc_messages) == 10:
            # something's wrong if there are 10 delayed messages, better try to reconnect
            await self.join_channels(irc_msg.channel)
            print(f'Try to rejoin #{irc_msg.channel}')  # TODO: modify the print into logging
            delayed_irc_messages.append(irc_msg)
        # protection from memory overflow
        elif len(delayed_irc_messages) == 30:
            print(f'#{irc_msg.channel} has delayed msgs overflow')  # TODO: modify the print into logging
            delayed_irc_messages.append(irc_msg)
        elif len(delayed_irc_messages) > 30:
            pass
        else:
            delayed_irc_messages.append(irc_msg)

    def _call_event(
            self,
            event_name: str,
            *args
    ):
        if (event := getattr(self, event_name, None)) is not None:
            self._do_later(
                event(*args)
            )

    def event(self, coro: Callable[..., Coroutine]) -> Callable[[], Coroutine]:
        """
        |DECORATOR|
        registers handler of event

        Args:
            coro: Coroutine
                a Coroutine that will be called when the event would be happened, should has known name of event

        Raises:
            errors.UnknownEvent
                if got unknown event's name
            errors.FunctionIsNotCoroutine
                if `coro` is not Coroutine

        Returns:
            Coroutine:
                the object that the method got in `coro` as argument
        """
        self._register_event(coro.__name__, coro)
        return coro

    def _register_event(
            self,
            handler_name: str,
            coro: Callable[..., Coroutine]
    ) -> None:
        """
        1. Registers event with given name.
        2. Checks that the `coro` is Coroutine.
        3. Checks that the `handler_name` is known.

        Args:
            handler_name: `str`
                name of handler, should be known
            coro: Coroutine
                coroutine that must handle specified event.

        Returns:
            `None`
        """
        if not iscoroutinefunction(coro):
            raise TypeError(f'given object `{coro.__name__}` is not a coroutine function')
        # if event
        if handler_name in self.EVENTS:
            setattr(self, handler_name, coro)
        # if user event
        elif handler_name in self.USER_EVENTS:
            setattr(self, handler_name, coro)
        else:  # what for a developer will register unknown event? better tell that person about
            raise NameError(f'"{handler_name}" is unknown name of event')

    @staticmethod
    def _do_later(
            coro: Awaitable
    ) -> None:
        """Creates async task in `self.loop`"""
        asyncio.get_event_loop().create_task(coro)

    _COMMAND_HANDLERS: Dict[str, Callable[['Client', TwitchIRCMsg], Any]] = {
        'PRIVMSG': _handle_privmsg,
        'WHISPER': _handle_whisper,
        'JOIN': _handle_join,
        'PART': _handle_part,
        'NOTICE': _handle_notice,
        'USERNOTICE': _handle_usernotice,
        'CLEARCHAT': _handle_clearchat,
        'CLEARMSG': _handle_clearmsg,
        'HOSTTARGET': _handle_hosttarget,
        'ROOMSTATE': _handle_roomstate,
        'USERSTATE': _handle_userstate,
        'GLOBALUSERSTATE': _handle_globaluserstate,
        'RECONNECT': _handle_reconnect,
        '353': _handle_names_part,
        '366': _handle_names_end
    }

    _USER_EVENT_TYPES: Dict[str, Tuple[str, Any]] = {
        # event_type(or 'msg-id'): (event_handler, event_class)
        'sub': ('on_sub', Sub),
        'resub': ('on_resub', ReSub),
        'subgift': ('on_sub_gift', SubGift),
        'submysterygift': ('on_sub_mystery_gift', SubMysteryGift),
        'primepaidupgrade': ('on_prime_paid_upgrade', PrimePaidUpgrade),
        'giftpaidupgrade': ('on_gift_paid_upgrade', GiftPaidUpgrade),
        'anongiftpaidupgrade': ('on_gift_paid_upgrade', GiftPaidUpgrade),
        'standardpayforward': ('on_standard_pay_forward', StandardPayForward),
        'communitypayforward': ('on_community_pay_forward', CommunityPayForward),
        'bitsbadgetier': ('on_bits_badge_tier', BitsBadgeTier),
        'ritual': ('on_ritual', Ritual),
        'raid': ('on_raid', Raid),
        'unraid': ('on_unraid', UnRaid)
    }

    EVENTS = (
        'on_message',  # PRIVMSG
        'on_whisper',  # WHISPER
        'on_channel_join', 'on_channel_update',  # ROOMSTATE
        'on_client_state_update',  # USERSTATE
        'on_names_update',  # 366
        'on_ready',  # GLOBALUSERSTATE
        'on_user_join',  # JOIN
        'on_user_part',  # PART
        'on_user_timeout', 'on_clear_chat',  # CLEARCHAT
        'on_message_delete',  # CLEARMSG
        'on_host_start', 'on_host_stop',  # HOSTTARGET
        'on_notice', 'on_channel_join_error', 'on_send_message_error',  # NOTICE
        'on_commands_update', 'on_mods_update', 'on_vips_update',  # NOTICE
        'on_user_event', 'on_unknown_user_event',  # USERNOTICE
        'on_reconnect', 'on_unknown_command',
    )

    USER_EVENTS = (
        'on_sub', 'on_resub', 'on_sub_gift', 'on_sub_mystery_gift',  # subs
        'on_prime_paid_upgrade', 'on_gift_paid_upgrade',  # upgrades
        'on_standard_pay_forward', 'on_community_pay_forward',  # payments forward
        'on_bits_badge_tier',  # bits badges tier
        'on_reward_gift',  # rewards
        'on_raid', 'on_unraid',  # raids
        'on_ritual',  # rituals
    )
