from odoo import tools, models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date,datetime


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    # Demo methods

    def _get_bom_all_product_qties_dict(self, product_dict={}):
        for bom_line in self.bom_line_ids:
            if not bom_line.product_id.bom_ids:
                if bom_line.product_id.id not in product_dict:
                    product_dict[bom_line.product_id.id] = ['Component',bom_line.product_qty,self.id]
            else:
                if bom_line.product_id.id not in product_dict:
                    product_dict[bom_line.product_id.id] = ['Sub-assembly - %s'%(bom_line.product_id.display_name),bom_line.product_qty,self.id]
                new_bom = bom_line.product_id.bom_ids[0]
                product_dict = new_bom._get_bom_all_product_qties_dict(product_dict)
        return product_dict

    def _compute_costs(self):
        for rec in self:
            product = rec.product_tmpl_id.product_variant_ids[0]
            rec.total_cost = product.standard_price
            rec.indirect_cost = product.indirect_cost
            rec.direct_cost = product.direct_cost

    def update_product_costs(self):
        for rec in self:
            product_ids = self.env['product.product'].search([('product_tmpl_id','=',rec.product_tmpl_id.id)])
            for product_id in product_ids:
                vals = {
                    'standard_price': rec.total_cost,
                    'indirect_cost': rec.indirect_cost,
                    'direct_cost': rec.direct_cost,
                    }
                product_id.write(vals)

    total_cost = fields.Float('Total Cost',compute=_compute_costs)
    indirect_cost = fields.Float('Direct Cost',compute=_compute_costs)
    direct_cost = fields.Float('Indirect Cost',compute=_compute_costs)

class MrpBomCost(models.Model):
    _name = 'mrp.bom.cost'
    _description = 'mrp.bom.cost'

    def btn_update_costs(self):
        self.ensure_one()
        for line in self.line_ids.filtered(lambda l: l.bom_id.id == self.bom_id.id):
            product_id = line.product_id
            product_id.standard_price = line.price_unit
            product_id.indirect_cost = line.indirect_cost
            product_id.direct_cost = line.direct_cost
            cost_id = self.env['product.product.cost'].search([('cost_id','=',self.id),('product_id','=',product_id.id)])
            vals = {
                'cost_id': self.id,
                'product_id': product_id.id,
                'date': str(date.today()),
                'total_unit_cost': line.standard_price,
                'direct_cost': line.direct_cost,
                'indirect_cost': line.indirect_cost,
                }
            if cost_id:
                cost_id.write(vals)
            else:
                cost_id = self.env['product.product.cost'].create(vals)



    def btn_fill_components(self):
        self.ensure_one()
        if not self.bom_id:
            raise ValidationError('Debe seleccionar la lista de materiales')
        for line in self.line_ids:
            line.unlink()
        products = self.bom_id._get_bom_all_product_qties_dict({})
        for key,values in products.items():
            product = self.env['product.product'].browse(key)
            price_unit = product.standard_price
            vals = { 
                    'cost_id': self.id,
                    'product_id': key,
                    'bom_id': values[2],
                    'qty': values[1] * self.qty,
                    'standard_price': product.standard_price,
                    'line_type': values[0],
                    'price_unit': price_unit,
                    'total_cost': price_unit * values[1] * self.qty,
                    'uom_id': self.env['product.product'].browse(key).uom_id.id,
                    }
            line_id = self.env['mrp.bom.cost.line'].create(vals)
            line_id._compute_items()


    def _compute_items(self):
        for rec in self:
            res = 0
            res1 = 0
            res2 = 0
            for item in rec.line_ids.filtered(lambda l: l.bom_id.id == rec.bom_id.id):
                res = res + item.price_unit * item.qty
                res1 = res1 + item.total_direct_cost
                res2 = res2 + item.total_indirect_cost
            rec.total_cost = res
            rec.total_direct_cost = res1
            rec.total_indirect_cost = res2

    def btn_show_components(self):
        self.ensure_one()
        self.only_components = True
        for line in self.line_ids:
            if not line.product_id.bom_ids:
                line.active = False

    def btn_show_all_items(self):
        self.ensure_one()
        self.only_components = False
        lines = self.env['mrp.bom.cost.line'].search([('cost_id','=',self.id),('active','=',False)])
        for line in lines:
            line.active = True

    def btn_show_first_level(self):
        self.ensure_one()
        self.only_components = True
        lines = self.env['mrp.bom.cost.line'].search([('cost_id','=',self.id),'|',('active','=',False),('active','=',True)])
        lines.write({'active': True})
        lines = self.env['mrp.bom.cost.line'].search([('cost_id','=',self.id),('bom_id','!=',self.bom_id.id)])
        lines.write({'active': False})



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
    temporary = fields.Boolean('temporary',default=False)
    only_components = fields.Boolean('Only components',default=False)

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

    def _compute_update_date(self):
        for rec in self:
            res = None
            if rec.product_id.cost_ids:
                res = str(rec.product_id.cost_ids[0].write_date)[:10]
            rec.update_date = res

    def _compute_line_item(self):
        for rec in self:
            res = 0
            items = self.env['mrp.bom.cost.line'].search([('cost_id','=',rec.cost_id.id),('id','<',rec.id)])
            if items:
                res = len(items)
            rec.line_item = res + 1

    def show_document(self):
        self.ensure_one()
        if self.line_type == 'Component':
            view_id = self.env.ref('product.product_normal_form_view').id
            res_model = 'product.product'
            res_id = self.product_id.id
            return {
                'name': _('Show document'),
                'res_model': res_model,
                'view_mode': 'form',
                'res_id': res_id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            view_id = self.env.ref('mrp_bom_costs.mrp_bom_cost_form').id
            res_model = 'mrp.bom.cost'
            vals = {
                    'name': self.product_id.name,
                    'bom_id': self.product_id.bom_ids[0].id,
                    'product_id': self.product_id.id,
                    'product_tmpl_id': self.product_id.product_tmpl_id.id,
                    'qty': self.qty,
                    'temporary': True,
                    }
            res_id = self.env['mrp.bom.cost'].create(vals)
            res_id.btn_fill_components()
            return {
                'name': _('Show document'),
                'res_model': 'mrp.bom.cost',
                'view_mode': 'form',
                'res_id': res_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }


    line_item = fields.Integer('#',compute=_compute_line_item)
    cost_id = fields.Many2one('mrp.bom.cost',string='Costo')
    product_id = fields.Many2one('product.product',string='Componente')
    bom_id = fields.Many2one('mrp.bom',string='BoM')
    qty = fields.Float('Cantidad')
    price_unit = fields.Float('Precio Unitario')
    standard_price = fields.Float('Costo')
    direct_cost = fields.Float('Costo Directo Unitario')
    indirect_cost = fields.Float('Costo Indirecto Unitario')
    uom_id = fields.Many2one('uom.uom',string='Unidad de medida')
    total_cost = fields.Float('Costo Total')
    total_direct_cost = fields.Float('Costo Directo Total')
    total_indirect_cost = fields.Float('Costo Indirecto Total')
    line_type = fields.Char('Tipo Componente')
    update_date = fields.Date('Fecha actualizacion',compute=_compute_update_date)
    tag_ids = fields.Many2many(comodel_name='product.tag',relname='tag_item_rel',col1='item_id',col2='tag_id',string='Tags')
    active = fields.Boolean('Active',default=True)

class ProductProductCost(models.Model):
    _inherit = 'product.product.cost'

    cost_id = fields.Many2one('mrp.bom.cost','Costo')
