# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    analytic_account_id = fields.Many2one('account.analytic.account', states={'done': [('readonly', True)]})
    account_id = fields.Many2one('account.account', states={'done': [('readonly', True)]})

    @api.model
    def create(self, vals):
        result = super(PurchaseOrder, self).create(vals)
        if 'account_id' in list(vals.keys()) and 'analytic_account_id' in list(vals.keys()):
            accountid = vals['account_id']
            analyticid = vals['analytic_account_id']
            budget_positions = self.env['account.budget.post'].search([('account_ids', 'in', [accountid])])
            lines = self.env['crossovered.budget.lines'].search([('analytic_account_id.id', '=', analyticid), ('general_budget_id', 'in', budget_positions.ids)])
            for line in lines:
                line.write({
                    'purchase_ids': [(4, result.id, 0)]
                })
        return result

    def write(self, vals):
        result = super(PurchaseOrder, self).write(vals)
        if any(item in ['account_id', 'analytic_account_id'] for item in vals.keys()):
            accountid = self.account_id.id
            analyticid = self.analytic_account_id.id
            budget_positions = self.env['account.budget.post'].search([('account_ids', 'in', [accountid])])
            lines = self.env['crossovered.budget.lines'].search([('analytic_account_id.id', '=', analyticid), ('general_budget_id', 'in', budget_positions.ids)])
            old_lines = self.env['crossovered.budget.lines'].search([('purchase_ids', 'in', [self.id])])
            for line in old_lines:
                line.write({
                    'purchase_ids': [(3, self.id, 0)]
                })
            for line in lines:
                line.write({
                    'purchase_ids': [(4, self.id, 0)]
                })
        return result