import quickfix as fix

class OrderClient:

    @staticmethod
    def create_order(
        marker_id: str,
        price: str,
        quantity: str,
        side_ch: str,
        order_type_ch: str,
        ord_clord_id: str,
        session_id: fix.SessionID
    ) -> bool:
        """Create a new order"""
        order = OrderClient.build_order(
            marker_id,
            price,
            quantity,
            side_ch,
            order_type_ch,
            ord_clord_id
        )
        return fix.Session.sendToTarget(order, session_id)

    @staticmethod
    def build_order(marker_id: str, price: str, quantity: str, side_ch: str,
                   order_type_ch: str, ord_clord_id: str) -> fix.Message:
        """Build a new order message"""
        order = fix.Message()
        order.getHeader().setField(fix.MsgType(fix.MsgType_NewOrderSingle))

        # Set order fields
        order.setField(fix.Symbol(marker_id))
        order.setField(fix.OrdType(order_type_ch))
        if order_type_ch == fix.OrdType_LIMIT:
            order.setField(fix.Price(float(price)))
        order.setField(fix.Side(side_ch))
        order.setField(fix.TimeInForce('1'))
        order.setField(fix.OrderQty(float(quantity)))
        order.setField(fix.ClOrdID(ord_clord_id))

        return order
