odoo.define('project_glasbox.ProjectGanttModel', function (require) {
"use strict";

var GanttModel = require('web_gantt.GanttModel');
var _t = require('web.core')._t;

var ProjectGanttModel = GanttModel.extend({

    _getFields: function () {
        var fields = this._super(...arguments);
        if (this.modelName == 'project.task'){
            fields.push('completion_date','user_id','task_delay','check_c_date','check_completion_date','date_end','milestone','on_hold','check_l_end_date', 'l_end_date', 'planned_duration', 'buffer_time')
        }
        return fields
    },

});

return ProjectGanttModel;
});