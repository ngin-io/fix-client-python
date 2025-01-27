#!/usr/bin/env python
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from typing import Set
from typing import Union
import logging
import logging
import time

import quickfix as fix

from fix_client import lib

logger = logging.getLogger(__name__)

def get_argument_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config.cfg")
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=logging._nameToLevel.keys(),  # Gets all valid logging levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
        help='Set the logging level'
    )
    return parser


def init_logger(log_level):
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True,
    )

class FixClientSampleApplication(lib.FixClientApplication):

    def __init__(self, settings: fix.SessionSettings):
        super().__init__(settings)
        self._rejected_orders: Set[str] = set()
        self.ord_clord_id: Optional[str] = None
        self.invalid_create_ord_clord_id: Optional[str] = None
        self.invalid_cancel_ord_clord_id: Optional[str] = None
        self.executor = ThreadPoolExecutor(max_workers=1)

    def fromApp(self, message: fix.Message, session_id: fix.SessionID):
        """Handle application messages"""
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)

        if msg_type.getValue() == fix.MsgType_ExecutionReport:
            self._handle_execution_report(message, session_id)
        elif msg_type.getValue() == fix.MsgType_Reject:
            self._handle_reject(message)
        elif msg_type.getValue() == fix.MsgType_Heartbeat:
            self._handle_heartbeat(message, session_id)

    def onLogon(self, session_id: fix.SessionID):
        """Handle logon event"""
        logger.info(f"--------- Logon - {session_id} ---------")

        if self._rejected_orders:
            return

        timestamp = self._current_timestamp_str()
        self.ord_clord_id = f"{self.CLORD_ID_PREFIX}{timestamp}"
        self.invalid_create_ord_clord_id = f"{timestamp}-{self.INV_ORD_CREATE_SUFFIX}"
        self.invalid_cancel_ord_clord_id = f"{timestamp}-{self.INV_ORD_CANCEL_SUFFIX}"

        time.sleep(self.SLEEP_TIME.total_seconds())
        self.executor.submit(self._send_create_order, session_id, self.ord_clord_id)

    def _handle_execution_report(self, message: fix.Message, session_id: fix.SessionID):
        """Handle execution reports"""
        if self._rejected_orders:
            return

        exec_type = fix.ExecType()
        message.getField(exec_type)

        clord_id = fix.ClOrdID()
        message.getField(clord_id)

        ord_status = fix.OrdStatus()
        message.getField(ord_status)

        if exec_type.getValue() == fix.ExecType_CANCELED:
            logger.info(f"--------- Received execution report for cancel order, Id: {clord_id.getValue()}, Status: {ord_status.getValue()}")
            return

        if exec_type.getValue() == fix.ExecType_ORDER_STATUS:
            logger.info(f"--------- Received execution report for order status: {ord_status.getValue()}")
            time.sleep(self.SLEEP_TIME.total_seconds())
            self.executor.submit(self._send_cancel_order, session_id, self.ord_clord_id)
            return

        if exec_type.getValue() not in [fix.ExecType_NEW, fix.ExecType_PARTIAL_FILL, fix.ExecType_TRADE]:
            logger.info(f"--------- Received unexpected execution report {exec_type.getValue()} from gateway")

        ord_type = fix.OrdType()
        message.getField(ord_type)

        if ord_type.getValue() == fix.OrdType_MARKET:
            logger.info(f"--------- Received execution report for market order, Id: {clord_id.getValue()}, Status: {ord_status.getValue()}")
        else:
            logger.info(f"--------- Received execution report for limit order, Id: {clord_id.getValue()}, Status: {ord_status.getValue()}")

        time.sleep(self.SLEEP_TIME.total_seconds())
        self.executor.submit(self._send_order_status, session_id, self.ord_clord_id)

    def _handle_reject(self, message: fix.Message):
        """Handle reject messages"""
        seq_num = fix.MsgSeqNum()
        message.getHeader().getField(seq_num)

        text = fix.Text()
        message.getField(text)

        logger.info(f"---------  Received order reject. Order: SeqNumber: [{seq_num.getValue()}]. Reason: [{text.getValue()}] ---------")

    def _handle_heartbeat(self, message: fix.Message, session_id: fix.SessionID):
        """Handle heartbeat messages"""
        sending_time = fix.SendingTime()
        message.getHeader().getField(sending_time)

        logger.info(f"--------- Heartbeat --------- SenderCompID: {session_id.getSenderCompID()}, SendTime: {sending_time.getString()}")

        order_types = {order.split('-')[1] for order in self._rejected_orders if '-' in order}

        if self.INV_ORD_CREATE_SUFFIX not in order_types:
            self.executor.submit(self._send_create_invalid_order, session_id, self.invalid_create_ord_clord_id)
            self._rejected_orders.add(self.invalid_create_ord_clord_id)
        elif self.INV_ORD_CANCEL_SUFFIX not in order_types:
            self.executor.submit(self._send_cancel_order, session_id, self.invalid_cancel_ord_clord_id)
            self._rejected_orders.add(self.invalid_cancel_ord_clord_id)
        else:
            logger.info("--------- Terminating app...")
            self.executor.shutdown(wait=True)
            import sys
            sys.exit(0)

    def _send_create_order(self, session_id: fix.SessionID, ord_clord_id: str):
        """Send a create order request"""
        try:
            is_sent = lib.OrderClient.create_order(
                "BAT-AUD",  # marker_id
                "5",        # price
                "0.1",      # quantity
                '1',        # side
                '2',        # order_type
                ord_clord_id,
                session_id
            )
            logger.info(f"Order create [{ord_clord_id}] sent? {is_sent}")
        except fix.SessionNotFound as e:
            logger.error(f"Failed to send create order: {e}")

    def _send_create_invalid_order(self, session_id: fix.SessionID, ord_clord_id: str):
        """Send an invalid create order request"""
        try:
            is_sent = lib.OrderClient.create_order(
                "BAT-AUD",          # marker_id
                "5",                # price
                "10000000000000",   # invalid quantity
                '1',                # side
                '2',                # order_type
                ord_clord_id,
                session_id
            )
            logger.info(f"Order create [{ord_clord_id}] sent? {is_sent}")
        except fix.SessionNotFound as e:
            logger.error(f"Failed to send create order: {e}")

    def _send_cancel_order(self, session_id: fix.SessionID, ord_clord_id: str):
        """Send a cancel order request"""
        try:
            new_ord_clord_id = f"{self.CLORD_ID_PREFIX}{self._current_timestamp_str()}"
            message = fix.Message()
            message.getHeader().setField(fix.MsgType(fix.MsgType_OrderCancelRequest))
            message.setField(fix.OrigClOrdID(ord_clord_id))
            message.setField(fix.ClOrdID(new_ord_clord_id))

            is_sent = fix.Session.sendToTarget(message, session_id)
            logger.info(f"Order cancel [{ord_clord_id}] sent? {is_sent}")
        except fix.SessionNotFound as e:
            logger.error(f"Failed to send cancel order: {e}")

    def _send_order_status(self, session_id: fix.SessionID, ord_clord_id: str):
        """Send an order status request"""
        try:
            message = fix.Message()
            message.getHeader().setField(fix.MsgType(fix.MsgType_OrderStatusRequest))
            message.setField(fix.ClOrdID(ord_clord_id))

            is_sent = fix.Session.sendToTarget(message, session_id)
            logger.info(f"Order status [{ord_clord_id}] sent? {is_sent}")
        except fix.SessionNotFound as e:
            logger.error(f"Failed to send order status: {e}")

def entrypoint(
        config: Path,
        log_level: Union[str, None] = None,
):
    if log_level:
        init_logger(log_level)
    settings = fix.SessionSettings(str(config))
    app = FixClientSampleApplication(settings)
    store_factory = fix.FileStoreFactory(settings)
    log_factory = fix.ScreenLogFactory(settings)
    initiator = fix.SSLSocketInitiator(
        app,
        store_factory,
        settings,
        log_factory,
    )
    initiator.start()
    while True:
        time.sleep(1)


def main():
    args = get_argument_parser().parse_args()
    entrypoint(
        config=args.config,
        log_level=args.log_level,
    )

if __name__ == "__main__":
    main()
