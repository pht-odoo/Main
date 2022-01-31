# -*- coding: utf-8 -*-
from datetime import timedelta, datetime, date
import pytz
from pytz import timezone, UTC
from odoo.exceptions import ValidationError, UserError
from odoo import models, fields, api, _

class DependingTasks(models.Model):
    _name = "project.depending.tasks"
    _description = "Tasks Dependency (m2m)"

    task_id = fields.Many2one('project.task', required=True, copy=True)
    project_id = fields.Many2one('project.project', string='Project', copy=True)
    depending_task_id = fields.Many2one('project.task', required=True, copy=True)
    relation_type = fields.Char('Relation', default="Finish To Start", copy=True)

class TaskDependency(models.Model):
    _inherit = "project.task"

    planned_duration = fields.Integer('Duration', default=1, copy=True)
    buffer_time = fields.Integer(string='Buffer Time', copy=True)
    task_delay = fields.Integer(string='Task Delay', compute='_compute_delay', store=True, copy=True)
    accumulated_delay = fields.Integer(string='Accumulated Delay', compute='_compute_accumulated_delay', store=True, copy=True)
    on_hold = fields.Integer(string="On Hold", copy=True)
    dependency_task_ids = fields.One2many('project.depending.tasks', 'depending_task_id', copy=True)
    date_start = fields.Datetime(string='Starting Date', compute='_compute_start_date', store=True, copy=True)
    date_end = fields.Datetime(string='Ending Date', readonly=True, compute='_compute_end_date', store=True, copy=True)
    completion_date = fields.Datetime(string='Completion Date', copy=True)
    check_end_or_comp_date = fields.Datetime(string='Checking End or Completion Date', compute='_compute_end_comp', store=True, copy=True)
    milestone = fields.Boolean(string='Mark as Milestone', default=False, copy=True)
    first_task = fields.Boolean(string='First Task', default=False, copy=True)
    l_start_date = fields.Datetime(string='Latest Start Date',compute='_compute_l_start_end_date', store=True, copy=True)
    l_end_date = fields.Datetime(string='Latest End Date', compute='_compute_l_start_end_date', store=True, copy=True)
    duration_mode = fields.Char(readonly=True, copy=True)
    delay_due_to = fields.Char(string="Delay Due To", copy=True)
    check_delay = fields.Boolean(string="Check Delay", compute="_compute_check_delay", copy=True)
    check_c_date = fields.Boolean(string='Check Whether the Completion Date is set or not', compute="_compute_c_date", store=True, copy=True)
    check_overdue = fields.Boolean(string='Check OverDue', compute="_check_completion_date", copy=True)
    check_milestone = fields.Boolean(string="Check Milestone", compute="_compute_milestone", copy=True)
    check_ahead_schedule = fields.Boolean(string="Check Ahead Of Schedule", compute="_compute_ahead", copy=True)
    check_hold = fields.Boolean(string="Check On Hold", compute="_check_hold", copy=True)
    scheduling_mode = fields.Selection([
        ("0", "Must Start On"),
        ("1", "Must Finish On"),
    ], string="Scheduling Mode", copy=True)

    def get_calendar(self):
        return self.env.company.resource_calendar_id

    def check_weekends(self):
        for record in self:
            resource_calendar = record.get_calendar()
            day_of_week = resource_calendar.attendance_ids.dayofweek

    def get_global_ids(self):
        return self.get_calendar().global_leave_ids

    def count_tasks(self):
        return len(self.dependency_task_ids.task_id)

    def get_work_days(self):
        '''
            Method for getting company's work_days(business_days) according to company's calendar.
        '''
        for record in self:
            resource_calendar = record.get_calendar()
            sum_hours = sum((attendance.hour_to - attendance.hour_from) for attendance in resource_calendar.attendance_ids)
            hour = resource_calendar.hours_per_day
            day_of_week = resource_calendar.attendance_ids
            return (sum_hours / hour)

    def get_holidays(self, start_date):
        '''
            Method for getting company's holiday's according to company's calendar and only one date.
            You will get holiday's date in list.
        '''
        for record in self:
            if record.l_end_date or record.completion_date or record.first_task or record.l_start_date:
                leaves = record.get_global_ids().filtered(lambda d: start_date and d.date_from.date() < start_date.date())
            else:
                leaves = record.get_global_ids().filtered(lambda d: start_date and d.date_from.date() > start_date.date())
            lst_days = []
            for leave in leaves:
                l_days = [leave.date_from.date()+timedelta(days=x) for x in range((leave.date_to.date()-leave.date_from.date()+timedelta(days=1)).days)]
                for days  in l_days:
                    lst_days.append(days)
            return lst_days

    def get_holidays_between_dates(self, start_date, end_date):
        '''
            Method for getting holiday's between two dates according to comapny's calendar.
            You will get holiday's date in list
        '''
        for record in self:
            work_days = record.get_work_days()
            daydiff = start_date.weekday() - end_date.weekday()
            working_days = ((start_date-end_date).days - daydiff) / 7 * work_days + min(daydiff,work_days) - (max(start_date.weekday() - 4, 0) % work_days)

            leaves = record.get_global_ids().filtered(lambda d: d.date_from.date() > start_date.date())
            lst_days = []
            for leave in leaves:
                l_days = [leave.date_from.date()+timedelta(days=x) for x in range((leave.date_to.date()-leave.date_from.date()+timedelta(days=1)).days)]
                # lst_days.append(days for days in l_days if start_date <= days <= end_date)
                for days  in l_days:
                    if start_date.date() <= days <= end_date.date():
                        lst_days.append(days)
            return (working_days - len(lst_days) if working_days > 0 else len(lst_days) + working_days)

    def get_forward_next_date(self, next_date):
        '''
            Method for calculating the 'end_date' according to any 'start_date'
        '''
        for record in self:
            duration = 0
            resource_calendar = record.get_calendar()
            day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
            holidays = record.get_holidays(next_date)
            duration = record.planned_duration + record.on_hold + record.buffer_time
            if next_date:
                next_date = next_date + timedelta(days=-1)
                while duration > 0:
                    next_date += timedelta(days=1)
                    if str(next_date.weekday()) not in day_of_week:
                        continue
                    if next_date in holidays:
                        continue
                    duration -= 1
                return next_date

    def get_forward_l_end_date(self, next_date):
        '''
            Method for calculating the 'l_end_date' according to any 'l_start_date'
        '''
        for record in self:
            duration = 0
            resource_calendar = record.get_calendar()
            day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
            holidays = record.get_holidays(next_date)
            duration = record.planned_duration
            if next_date:
                next_date = next_date + timedelta(days=-1)
                while duration > 0:
                    next_date += timedelta(days=1)
                    if str(next_date.weekday()) not in day_of_week:
                        continue
                    if next_date in holidays:
                        continue
                    duration -= 1
                return next_date

    def get_backward_next_date(self,previous_date):
        '''
            Method for calculating 'start_date' according to any 'end_date'
        '''
        for record in self:
            resource_calendar = record.get_calendar()
            day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
            duration = record.planned_duration - 1
            holidays = record.get_holidays(previous_date)
            if previous_date:
                while duration > 0:
                    previous_date -= timedelta(days=1)
                    if str(previous_date.weekday()) not in day_of_week:
                        continue
                    if previous_date in holidays:
                        continue
                    duration -= 1
                return previous_date

    def check_date_weekend(self, date):
        '''
            Method for to check whether the 'date' is in weekend or not.
            If the date is in weekend then we will update that date according to company's workday.
        '''
        for record in self:
            resource_calendar = record.get_calendar()
            day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
            if date and str(date.weekday()) not in day_of_week:
                s_date = date + timedelta(days=1)
                date = record.check_date_weekend(s_date)
            return date

    def date_in_holiday(self, date):
        '''
            Method for to check 'date' is in holiday or not.
            If 'date' is in holiday then we will increment date by one day and check that 'date' is in weekend or not.
            If 'date' is not in holiday then we will increment date through one day and check that 'date' is in weekend or not. 
        '''
        for record in self:
            holidays = record.get_holidays(date)
            if date and date not in holidays:
                date += timedelta(days=1)
                date = record.check_date_weekend(date)

            if date in holidays:
                date += timedelta(days=1)
                date = record.check_date_weekend(date)
            return date

    def _send_mail_template(self):
        for record in self:
            '''
                Method for sending mail to the assigned user of A3 task, when it's dependent tasks 
                A1's completion date is set and A2's completion date is not set.
                Whenever, A2's completion date is set, mail will be automatically sent to the A3 Task's
                assigned user.
            '''
            template = record.env.ref('project_glasbox.task_completion_email_template')
            tasks = record.env['project.task'].search([('dependency_task_ids.task_id', 'in', record.ids)])
            tasks.message_post_with_template(template_id=template.id)

    def write(self, vals):
        # OVERRIDE to write method
        '''
            If the A1 completion date is set but the A2 completion date is not set,
            Until A2's completion date is set, A3 starting date will get updated according to
            A2's completion date (because A2 is the latest completion date then A1)
        '''
        res = super().write(vals)
        for record in self:
            task_count = record.count_tasks()
            if 'completion_date' in vals and vals['completion_date']:
                date_start = datetime.strptime(vals['completion_date'],"%Y-%m-%d %H:%M:%S")
                tasks = record.env['project.task'].search([('dependency_task_ids.task_id', 'in', record.ids)])
                if task_count == 0:
                    tasks.write({
                        'date_start': False,
                        'date_end': False
                        })
                tasks.write({'date_start': record.date_in_holiday(date_start)})
                record._send_mail_template()
        return res

    @api.onchange('completion_date')
    def onchange_completion_date(self):
        '''
            The Completion date can only be today’s date! 
            Nobody can set yesterday's or next week’s date as the completion date.
        '''
        ctx = self.env.context
        for record in self:
            if ctx.get('c_date') and record.completion_date:
                record.completion_date = datetime.now()
                holidays = record.get_holidays(record.completion_date)
                resource_calendar = record.get_calendar()
                day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
                if record.completion_date and str(record.completion_date.weekday()) not in day_of_week:
                    raise UserError(_('You can not set Completion Date Which is not in your Working days! Kindly Check your Company Calendar!'))
                if record.completion_date and record.completion_date in holidays:
                    raise UserError(_('You can not set Completion Date Which is in Holidays! Kindly Check your Company Calendar!'))

    @api.onchange('dependency_task_ids', 'milestone', 'l_start_date')
    def onchange_changes(self):
        for record in self:
            resource_calendar = record.get_calendar()
            day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
            task_count = record.count_tasks()
            if record.milestone and record.dependency_task_ids:
                holidays_l_start_date = record.get_holidays(record.l_start_date)
                holidays_l_end_date = record.get_holidays(record.l_end_date)
                '''
                    For none milestone task, 'l_start_date' will be calculated when the milestone tasks’ Latest start/end date got inserted. 
                    Use the current task calculated Latest end date -  current task Duration (but not buffer time) - current task On hold (if any). 
                    Read-only field for non-milestone tasks.
                '''
                '''
                    For none milestone task, 'l_end_date' is calculate with the next tasks’ latest start date minus one business day. 
                    This will be the read-only field.
                '''
                l_end_cal = record.l_start_date - timedelta(days=1) if record.l_start_date else False
                for task in record.dependency_task_ids:
                    if task_count == 0:
                        task.task_id.l_start_date =  False
                        task.task_id.l_end_date = False
                    elif not task.task_id.milestone and not task.task_id.l_start_date and not task.task_id.l_end_date and l_end_cal:
                        while str(l_end_cal.weekday()) not in day_of_week:
                            l_end_cal -= timedelta(days=1)
                        while l_end_cal in holidays_l_end_date:
                            l_end_cal -= timedelta(days=1)
                        task.task_id.l_end_date = l_end_cal
                        l_start_cal = task.task_id.l_end_date - timedelta(task.task_id.planned_duration) - timedelta(task.task_id.on_hold) + timedelta(days=1)
                        while str(l_start_cal.weekday()) not in day_of_week:
                            l_start_cal -= timedelta(days=1)
                        while l_start_cal in holidays_l_start_date:
                            l_start_cal -= timedelta(days=1)
                        task.task_id.l_start_date = l_start_cal

    @api.depends('completion_date', 'date_end')
    def _compute_end_comp(self):
        for task in self:
            if task.completion_date and task.date_end and task.completion_date > task.date_end:
                task.check_end_or_comp_date = task.completion_date
            else:
                task.check_end_or_comp_date = task.date_end

    @api.depends('completion_date')
    def _compute_c_date(self):
        for task in self:
            if not task.completion_date:
                task.check_c_date = False
            else:
                task.check_c_date = True

    @api.depends('task_delay', 'check_c_date')
    def _compute_check_delay(self):
        for task in self:
            if task.task_delay > 0:
                task.check_delay = True
            else:
                task.check_delay = False

    @api.depends('completion_date', 'l_end_date')
    def _check_completion_date(self):
        for task in self:
            if task.completion_date and task.l_end_date and task.completion_date > task.l_end_date:
                task.check_overdue = True
            else:
                task.check_overdue = False

    @api.depends('on_hold','check_c_date')
    def _check_hold(self):
        for task in self:
            if task.on_hold > 0:
                task.check_hold = True
            else:
                task.check_hold = False

    @api.depends('milestone')
    def _compute_milestone(self):
        for task in self:
            if task.milestone:
                task.check_milestone = True
            else:
                task.check_milestone = False

    @api.depends('completion_date', 'date_end')
    def _compute_ahead(self):
        for task in self:
            if task.completion_date and task.date_end and task.completion_date < task.date_end:
                task.check_ahead_schedule = True
            else:
                task.check_ahead_schedule = False

    @api.depends('completion_date','date_end')
    def _compute_delay(self):
        '''
            Method For calculating the 'task_delay' based on the 'completion_date' and 'date_end'.
            task_delay = completion_date - date_end
            Here, you will get 'negative delay' if task finished if the task finished earlier than planned.
        '''
        # self.ensure_one()
        for record in self:
            if record.date_end and record.completion_date:
                # start_date = record.completion_date
                # end_date = record.date_end
                record.task_delay = record.get_holidays_between_dates(record.completion_date, record.date_end)
            if not record.completion_date:
                record.task_delay = 0

    @api.depends('dependency_task_ids.task_id.completion_date')
    def _compute_accumulated_delay(self):
        for record in self:
            task_count = record.count_tasks()
            # if task_count = 0 it means that no task is set as a 'dependent task'
            if task_count == 0:
                if record.dependency_task_ids:
                    record.accumulated_delay = 0 # set 'accumulated_delay' is 0 if no dependent task is set
                else:
                    record.accumulated_delay = record.accumulated_delay
            else:
                '''
                    Only fill in accumulated delay when all previous dependent tasks have a completion date.
                '''
                # list of all the 'completion_date' of the each dependent task
                completion_date_lst = record.dependency_task_ids.task_id.mapped('completion_date')
                if False in completion_date_lst:
                    record.accumulated_delay = 0
                else:
                    '''
                        If current task is not 'first_task' and it has dependent tasks and 'taks_count' is 1 and the dependent task is 'first_task'
                        then set 'accumulated_delay' = dependent task's 'task_delay' + current task's task_delay
                    '''
                    if task_count == 1 and record.dependency_task_ids.task_id['first_task']:
                        record.accumulated_delay = record.dependency_task_ids.task_id['task_delay'] + record.task_delay
                    elif task_count > 1 and False not in completion_date_lst and all(record.dependency_task_ids.task_id.mapped('first_task')):
                        delay_lst = record.dependency_task_ids.task_id.mapped('task_delay')
                        record.accumulated_delay = max(sorted(delay_lst)) + record.task_delay
                    else:
                        delay_lst = record.dependency_task_ids.task_id.mapped('accumulated_delay')
                        record.accumulated_delay = max(sorted(delay_lst)) + record.task_delay

    @api.depends('dependency_task_ids.task_id.completion_date')
    def _compute_start_date(self):
        for record in self:
            task_count = record.count_tasks()
            holidays = record.get_holidays(record.date_start)
            resource_calendar = record.get_calendar()
            day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
            if task_count == 0:
                if record.dependency_task_ids:
                    record.date_start = False
                    record.date_end = False
                if record.date_start and str(record.date_start.weekday()) not in day_of_week:
                    raise UserError(_('You can not set Start Date Which is not in your Working days! Kindly Check your Company Calendar!'))
                if record.date_start and record.date_start.date() in holidays:
                    raise UserError(_('You can not set Start Date Which is in Holidays! Kindly Check your Company Calendar!'))
            else:
                if not record.first_task and record.dependency_task_ids:
                    '''
                        If task_count = 1 and it has only one dependent task and that dependent task has 'completion_date' is set 
                        then current task's 'date_start' = previous task's completion_date + 1.
                    '''
                    # list of all the 'completion_date' of the each dependent task
                    completion_date_lst = record.dependency_task_ids.task_id.mapped('completion_date')
                    end_date_lst = record.dependency_task_ids.task_id.mapped('date_end')
                    first_element = completion_date_lst[0]
                    if task_count == 1 and len(completion_date_lst) == 1 and completion_date_lst[0] != False:
                            record.date_start = record.date_in_holiday(record.dependency_task_ids.task_id.completion_date)
                    elif False in completion_date_lst:
                        '''
                            If we have only one value in 'completion_date_lst' and the value is False
                            then current task's 'date_start' is previous task's 'end_date' + 1
                        '''
                        if len(completion_date_lst) == 1 and not completion_date_lst[0]:
                            record.date_start = record.date_in_holiday(end_date_lst[0])
                        elif len(completion_date_lst) > 1 and all(([completion_date_lst[i] == False for i in range(len(completion_date_lst))])):
                            max_end_date = max(sorted(end_date_lst))
                            record.date_start = record.date_in_holiday(max_end_date)
                        else:
                            '''
                                If A1 completion date is set but A2 completion date is not set,
                                then use A1 completion date +1 business day as A3 starting date.
                            '''
                            for i in range(len(completion_date_lst)):
                                previous_el = completion_date_lst[i-1]
                                if completion_date_lst[i] == False:
                                    # finding the number of times 'False' we are getting in list
                                    occurrences = completion_date_lst.count(False)
                                    if occurrences == 1:
                                        if previous_el and previous_el != False:
                                            record.date_start = record.date_in_holiday(previous_el)
                                        elif previous_el:
                                            # if occurrences are > 1 then, we will take max date from completion_date list
                                            max_comp_date = max(sorted(completion_date_lst))
                                            record.date_start = record.date_in_holiday(max_comp_date)
                                    else:
                                        start_date = record.date_in_holiday(previous_el)
                                        record.date_start = record.date_in_holiday(start_date)
                    else:
                        for date_start in completion_date_lst:
                            if date_start != first_element and False not in completion_date_lst:
                                '''
                                    If 'first_element' of 'completion_date' is not equal to 'date' 
                                    then 'date_start' of the current task will be calculated from the previous task 
                                    (take all the dependent task and take 'max_date' from all the dependent task) completion date 
                                    (use ending date if completion date is not set) + 1
                                '''
                                max_date_start = max(sorted(completion_date_lst))
                                start_date = record.date_in_holiday(max_date_start)
                                record.date_start = record.date_in_holiday(start_date + timedelta(days=1))
                            elif not date_start and False not in end_date_lst and len(completion_date_lst) == 0:
                                max_end_date = max(sorted(end_date_lst))
                                start_date = record.date_in_holiday(max_end_date)
                                record.date_start = record.date_in_holiday(start_date + timedelta(days=1))
                            else:
                                '''
                                    If 'completion_date' of the previous tasks are same in the 'date_lst' then
                                    we simply set set 'date_start' as a 'first_element' + 1
                                '''
                                start_date = record.date_in_holiday(first_element)
                                record.date_start = record.date_in_holiday(start_date + timedelta(days=1))

    @api.depends('planned_duration', 'buffer_time', 'on_hold', 'date_start')
    def _compute_end_date(self):
        '''
            Method for to set 'date_end' dynamically (applied forward calculation) according to 'date_start', 'planned_duration', 'buffer_time' and 'on_hold'.

            Here, the calculation of 'date_end' is as follows:-
            date_end = date_start + planned_duration + buffer_time + on_hold
        '''
        for record in self:
            sum_all = record.planned_duration + record.on_hold + record.buffer_time
            start_date = record.date_start
            if record.first_task or start_date:
                record.date_end = record.get_forward_next_date(record.date_start)

    @api.depends('l_end_date','l_start_date','planned_duration','milestone','scheduling_mode')
    def _compute_l_start_end_date(self):
        '''
            Method for to set 'l_start_date' dynamically (applied backward calculation) according to
            'l_end_date' and 'planned_duration'

            Here, the calculation of 'l_start_date' is as follows:-
            l_start_date = l_end_date - planned_duration

            Here, the calculation of 'l_end_date' is as follows:-
            l_end_date = l_date_start + planned_duration
        '''
        for record in self:
            holidays_l_start_date = record.get_holidays(record.l_start_date)
            holidays_l_end_date = record.get_holidays(record.l_end_date)
            resource_calendar = record.get_calendar()
            day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
            if record.l_start_date and str(record.l_start_date.weekday()) not in day_of_week or record.l_end_date and str(record.l_end_date.weekday()) not in day_of_week:
                raise UserError(_('You can not set Date Which is not in your Working days! Kindly Check your Company Calendar!'))
            if record.l_start_date and record.l_start_date.date() in holidays_l_start_date or record.l_end_date and record.l_end_date.date() in holidays_l_end_date:
                raise UserError(_('You can not set Date Which is in Holidays! Kindly Check your Company Calendar!'))
            if record.milestone and record.scheduling_mode == '1' and record.l_end_date:
                record.l_start_date = record.get_backward_next_date(record.l_end_date)
            elif record.milestone and record.scheduling_mode == '0' and record.l_start_date:
                record.l_end_date = record.get_forward_l_end_date(record.l_start_date)