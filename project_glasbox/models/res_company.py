# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class Company(models.Model):
    _inherit = "res.company"

    def write(self, vals):
        res = super(Company, self).write(vals)
        if vals.get('resource_calendar_id'):
            tasks = self.env['project.task'].search(['|', ('company_id', '=', False), ('company_id', '=', self.id)])

            # Check if the start date of the first tasks is on a holiday. If so, recompute it.
            first_tasks = tasks.filtered(lambda t: t.first_task)
            for task in first_tasks:
                holidays = task.get_holidays(task.date_start)
                if task.date_start and task.date_start.date() in holidays:
                    task.write({'date_start': task.get_next_business_day(task.date_start)})
            tasks._compute_holiday_days()
        return res
