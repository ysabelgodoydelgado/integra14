from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import UserError
from pytz import *
import re

import logging
_logger = logging.getLogger(__name__)

class BinauralHrWorkEntryInherit(models.Model):
    _inherit = 'hr.work.entry'
    _description = 'Herencia para personalizacion de entradas de trabajo'

    @api.onchange('work_entry_type_id')
    def _onchange_work_entry_type(self):                           
        if self.work_entry_type_id.name != False:            
            regexp = re.compile(r'nocturn*')        
            if regexp.search(self.work_entry_type_id.name):
                if self.date_start and self.date_stop:    
                    date_start = self.date_start.astimezone(timezone(self.env.user.tz))                    

                    if date_start.hour < 17:
                        raise UserError('Debe usar el tipo de entrada nocturna en un rango comprendido entre las 5pm y las 5am')
