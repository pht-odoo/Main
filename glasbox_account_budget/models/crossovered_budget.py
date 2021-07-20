# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    date_from = fields.Date('Start Date', required=False, states={'done': [('readonly', True)]})

class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    sale_ids = fields.Many2many('sale.order', string="Sale Orders")
    purchase_ids = fields.Many2many('purchase.order', string="Purchase Orders")
    planned_amount = fields.Monetary(
        'Planned Amount', required=True, store=True, readonly=False,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.",
        compute="_compute_planned_amount")

    @api.depends('sale_ids','purchase_ids','sale_ids.amount_untaxed','purchase_ids.amount_untaxed')
    def _compute_planned_amount(self):
        for line in self:
            line.planned_amount = 0
            for sale in line.sale_ids:
                line.planned_amount += sale.amount_untaxed
            for purchase in line.purchase_ids:
                line.planned_amount += purchase.amount_untaxed

    @api.depends('planned_amount','practical_amount')
    def _compute_theoritical_amount(self):
        for line in self:
            line.theoritical_amount = line.planned_amount - line.practical_amount

    @api.depends('planned_amount','practical_amount')
    def _compute_percentage(self):
        for line in self:
            if line.planned_amount != 0.00:
                line.percentage = line.practical_amount/line.planned_amount 
            else:
                line.percentage = 0.00