from odoo import tools, models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date,datetime


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    # Demo methods

    def _get_bom_product_qties_dict(self, product_dict={}):
        for bom_line in self.bom_line_ids:
            if not bom_line.product_id.bom_ids:
                if bom_line.product_id.id not in product_dict:
                    product_dict[bom_line.product_id.id] = bom_line.product_qty
            else:
                new_bom = bom_line.product_id.bom_ids[0]
                product_dict = new_bom._get_bom_product_qties_dict(product_dict)
        return product_dict



class MrpBomCost(models.Model):
    _name = 'mrp.bom.cost'
    _description = 'mrp.bom.cost'

    def btn_fill_components(self):
        self.ensure_one()
        if not self.bom_id:
            raise ValidationError('Debe seleccionar la lista de materiales')
        for line in self.line_ids:
            line.unlink()
        products = self.bom_id._get_bom_product_qties_dict({})
        for key,value in products.items():
            product = self.env['product.product'].browse(key)
            vals = { 
                    'cost_id': self.id,
                    'product_id': key,
                    'qty': value * self.qty,
                    'standard_price': product.standard_price,
                    'total_cost': product.standard_price * value * self.qty,
                    'uom_id': self.env['product.product'].browse(key).uom_id.id,
                    }
            line_id = self.env['mrp.bom.cost.line'].create(vals)


    def _compute_items(self):
        for rec in self:
            res = 0
            res1 = 0
            res2 = 0
            for item in rec.line_ids:
                res = res + item.total_cost
                res1 = res1 + item.total_direct_cost
                res2 = res2 + item.total_indirect_cost
            rec.total_cost = res
            rec.total_direct_cost = res1
            rec.total_indirect_cost = res2

    name = fields.Char('Nombre')
    bom_id = fields.Many2one('mrp.bom',string='Lista de Materiales')
    product_tmpl_id = fields.Many2one('product.template',string='Producto',related='bom_id.product_tmpl_id')
    product_id = fields.Many2one('product.product',string='Producto',related='bom_id.product_id')
    date = fields.Date('Fecha',default=fields.Date.today())
    qty = fields.Integer('Cantidad',default=1)
    line_ids = fields.One2many(comodel_name='mrp.bom.cost.line',inverse_name='cost_id',string='Lineas')
    total_cost = fields.Float('Costo Total',compute=_compute_items)
    total_direct_cost = fields.Float('Costo Directo Total',compute=_compute_items)
    total_indirect_cost = fields.Float('Costo Indirecto Total',compute=_compute_items)

class MrpBomCostLine(models.Model):
    _name = 'mrp.bom.cost.line'
    _description = 'mrp.bom.cost.line'

    def _compute_items(self):
        for rec in self:
            res = 0
            res1 = 0
            res2 = 0
            if rec.product_id:
                res = rec.product_id.standard_price
                res1 = rec.product_id.direct_cost
                res2 = rec.product_id.indirect_cost
            rec.direct_cost = res1
            rec.indirect_cost = res2
            rec.total_direct_cost = res1 * rec.qty
            rec.total_indirect_cost = res2 * rec.qty

    cost_id = fields.Many2one('mrp.bom.cost',string='Costo')
    product_id = fields.Many2one('product.product',string='Componente')
    qty = fields.Float('Cantidad')
    standard_price = fields.Float('Costo')
    direct_cost = fields.Float('Costo Directo Unitario',compute=_compute_items)
    indirect_cost = fields.Float('Costo Indirecto Unitario',compute=_compute_items)
    uom_id = fields.Many2one('uom.uom',string='Unidad de medida')
    total_cost = fields.Float('Costo Total')
    total_direct_cost = fields.Float('Costo Directo Total',compute=_compute_items)
    total_indirect_cost = fields.Float('Costo Indirecto Total',compute=_compute_items)
