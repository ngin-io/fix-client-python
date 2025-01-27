from datetime import datetime
from datetime import timedelta
from datetime import timezone
import base64
import hashlib
import hmac
import logging

import quickfix as fix

from fix_client.order import OrderClient

logger = logging.getLogger(__name__)

class FixClientApplication(fix.Application):

    CLORD_ID_PREFIX = "ID-"
    INV_ORD_CREATE_SUFFIX = "InvalidOrderCreate"
    INV_ORD_CANCEL_SUFFIX = "InvalidOrderCancel"
    SLEEP_TIME = timedelta(seconds=2)


    def __init__(self, settings: fix.SessionSettings):
        super().__init__()
        self.settings = settings

    def fromAdmin(self, message: fix.Message, session_id: fix.SessionID):
        logger.debug("Received fromAdmin callback.")

    def fromApp(self, message: fix.Message, session_id: fix.SessionID):
        """Route incoming application messages to their handlers"""
        logger.debug("Received fromApp callback.")

    def onCreate(self, session_id: fix.SessionID):
        logger.debug("Received onCreate callback.")
        self._set_sessions(session_id)

    def onLogon(self, session_id: fix.SessionID):
        """Handle logon event"""
        logger.debug("Received onLogon callback.")

    def onLogout(self, session_id: fix.SessionID):
        logger.debug(f"Received onLogout callback.")
        logger.info(f"Session {session_id} logout !")

    def toAdmin(self, message: fix.Message, session_id: fix.SessionID):
        logger.debug("Received toAdmin callback.")
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)
        if msg_type.getValue() == fix.MsgType_Logon:
            logger.debug("Received Logon request (toAdmin)")
            self._do_logon(message, session_id)

    def toApp(self, message: fix.Message, session_id: fix.SessionID):
        logger.debug("Received toApp callback.")

    def _set_sessions(self, session_id: fix.SessionID):
        if not hasattr(self, "_session_id_to_pk"):
            self._session_id_to_pk = {}
        self._session_id_to_pk[str(session_id)] = self.settings.get(session_id).getString("PrivateKey")

    def _do_logon(self, message: fix.Message, session_id: fix.SessionID) -> None:
        signed_message = sign_message(
            1,
            fix.MsgType_Logon,
            self._get_sender_comp_id(session_id),
            self._get_sending_time(message),
            self._session_id_to_pk[str(session_id)],
        )
        logger.debug(f"{signed_message=}")
        message.setField(fix.RawData(signed_message))
        message.setField(fix.RawDataLength(len(signed_message)))
        logger.debug(f"Login message: {message.toString().replace('\x01', '|')}")

    def _get_sending_time(self, message: fix.Message) -> str:
        """Get sending time in milliseconds since epoch."""
        sending_time = fix.SendingTime()
        message.getHeader().getField(sending_time)
        time_str = str(sending_time).split('=')[-1].split('\x01')[0]
        dt = datetime.strptime(time_str, "%Y%m%d-%H:%M:%S.%f").replace(tzinfo=timezone.utc)
        return str(int(dt.timestamp() * 1000))

    def _get_sender_comp_id(self, session_id: fix.SessionID):
        return str(session_id.getSenderCompID()).split("=")[-1].split('\x01')[0]

    @staticmethod
    def _current_timestamp_str() -> str:
        """Get current timestamp in milliseconds since epoch, matching FIX format"""
        dt = datetime.now(timezone.utc)
        # First format to match the FIX timestamp format
        time_str = dt.strftime("%Y%m%d-%H:%M:%S.%f")
        # Then parse it back, just like in _get_sending_time
        dt = datetime.strptime(time_str, "%Y%m%d-%H:%M:%S.%f").replace(tzinfo=timezone.utc)
        return str(int(dt.timestamp() * 1000))







def sign_message(
        seq_num: int,
        msg_type: str,
        api_key: str,
        timestamp: str,
        private_key: str,
) -> str:
    msg = f"{seq_num}{msg_type}{api_key}{timestamp}"
    logger.debug(f"Concatenated message: {msg=}")
    secret_bytes = base64.b64decode(private_key)
    signature = hmac.new(secret_bytes, msg.encode('utf-8'), hashlib.sha512).digest()
    return base64.b64encode(signature).decode('utf-8')
