# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelView, Workflow
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Lot', 'ShipmentIn']


class Lot(metaclass=PoolMeta):
    __name__ = 'stock.lot'

    def _on_change_product_cost_lines(self):
        pool = Pool()
        Move = pool.get('stock.move')
        PurchaseLine = pool.get('purchase.line')

        context = Transaction().context
        if context.get('from_move'):
            move = Move(context['from_move'])
            if (hasattr(move, 'origin') and move.origin and
                    isinstance(move.origin, PurchaseLine)):
                return
        super(Lot, self)._on_change_product_cost_lines()


class ShipmentIn(metaclass=PoolMeta):
    __name__ = 'stock.shipment.in'

    @classmethod
    @ModelView.button
    @Workflow.transition('received')
    def receive(cls, shipments):
        pool = Pool()
        LotCostLine = pool.get('stock.lot.cost_line')

        super(ShipmentIn, cls).receive(shipments)

        for shipment in shipments:
            for in_move in shipment.incoming_moves:
                if in_move.state != 'done' or not in_move.lot:
                    continue
                cost_line_vals = shipment._get_lot_cost_line_vals(in_move)
                if cost_line_vals:
                    LotCostLine.create(cost_line_vals)

    def _get_lot_cost_line_vals(self, incomming_move):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        PurchaseLine = pool.get('purchase.line')
        Uom = pool.get('product.uom')

        if (not incomming_move.lot
                or not isinstance(incomming_move.origin, PurchaseLine)):
            return None

        cost_lines = []
        default_category_id = ModelData.get_id('purchase_lot_cost',
            'cost_category_purchase_cost')
        if incomming_move.purchase_unit_price:
            unit_price = Uom.compute_price(incomming_move.purchase_unit,
                incomming_move.purchase_unit_price,
                incomming_move.product.default_uom)
        else:
            unit_price = incomming_move.product.cost_price
        cost_lines.append({
                'lot': incomming_move.lot.id,
                'category': default_category_id,
                'unit_price': unit_price,
                'origin': 'stock.move,%s' % incomming_move.id,
                })

        if getattr(incomming_move, 'unit_shipment_cost', False):
            shipment_category_id = ModelData.get_id('stock_lot_cost',
                'cost_category_shipment_cost')
            unit_shipment_cost = Uom.compute_price(incomming_move.uom,
                incomming_move.unit_shipment_cost,
                incomming_move.product.default_uom)
            cost_lines.append({
                    'lot': incomming_move.lot.id,
                    'category': shipment_category_id,
                    'unit_price': unit_shipment_cost,
                    'origin': 'stock.move,%s' % incomming_move.id,
                    })
        return cost_lines
