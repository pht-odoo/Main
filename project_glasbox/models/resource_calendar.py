# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    def write(self, vals):
        """
        Recomputes dates of tasks that depend on these calendars
        """
        res = super(ResourceCalendar, self).write(vals)
        if vals.get('attendance_ids') or vals.get('global_leave_ids'):
            companies = self.env['res.company'].sudo().search([('resource_calendar_id', '=', self.ids)])
            tasks = self.env['project.task'].search(
                ['|', ('company_id', '=', False), ('company_id', 'in', companies.ids)])

            # 1. Check if the start date of the first tasks is on a holiday. If so, recompute it.
            first_tasks = tasks.filtered(lambda t: t.first_task)
            for task in first_tasks:
                holidays = task.get_holidays(task.first_task)
                if task.date_start and task.date_start.date() in holidays:
                    task.write({'date_start': task.get_forward_next_date(task.date_start, 1)})

            tasks._compute_holiday_days()
        return res