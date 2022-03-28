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
            tasks._compute_holiday_days()
        return res