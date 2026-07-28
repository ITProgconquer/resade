# -*- coding: utf-8 -*-
from num2words import num2words
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools.float_utils import float_round as round


class hr_contract(models.Model):
    _name = 'hr.contract'
    _description = 'Contract'
    _inherit = "hr.contract"
 
    typeemp = fields.Selection([('cadre','Cadre'),('noncadre','Non cadre')], string='Type employé', required=True)
    modep = fields.Selection([('virement','Virement'),('cheque','Chèque'),('espece','Espèces')], string='Mode paiement', required=True)
    sursal = fields.Float("Sursalaire")
    indlog = fields.Float("Indemnité de logement")
    indtrans = fields.Float("Indemnité de transport")
    indfonc = fields.Float("Indemnité de fonction")
    pcaisse = fields.Float("Indemnité de caisse")
    pex = fields.Float("Prime exceptionelle")
    pnuit = fields.Float("Prime de nuit")
    pres = fields.Float("Prime de responsabilité")
    pex = fields.Float("Prime exceptionelle")
    aprime = fields.Float("Autre")
    indfor = fields.Float("Indemnité forfaitaire")
    indspec = fields.Float("Indemnité spécifique")
    indast = fields.Float("Indemnité astreinte")
    indtech = fields.Float("Indemnité de technicité")
    indexp = fields.Float("Indemnité exp réseau")
    alloc = fields.Float("Allocation familiale")
    carfo = fields.Boolean('Carfo')
    
    bruti = fields.Float("Brut initial")
    neti = fields.Float("Net imposable initial")
    chargesali = fields.Float("Charge sal. initial")
    chargepati = fields.Float("Charge pat. initial")
    heureti = fields.Float("Heures travaillés initial")
    heuresupi = fields.Float("Heures sup initial")
    congeaci = fields.Float("Congés acquis initial")
    congepi = fields.Float("Congés pris initial")
    

class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _description = 'Salary rule'
    _inherit = "hr.salary.rule"

    ref = fields.Char('Référence')

class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    _inherit = "hr.payslip"
    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        wentry = self.env['hr.work.entry.type'].search([('code','=','WORK100')])[0]
        attendance_line = {
                'sequence': wentry.sequence,
                'work_entry_type_id': wentry.id,
                'number_of_days': 30,
                'number_of_hours': 173,
            }
        res.append(attendance_line)
        return res
    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        wentry = self.env['hr.work.entry.type'].search([('code','=','WORK100')])[0]
        res.append({
                    'sequence': wentry.sequence,
                    'work_entry_type_id': wentry.id,
                    'number_of_days': 30,
                    'number_of_hours': 173,
                })
        return res
    def brouillon(self):
        self.write({'state': "draft"})

    @api.depends('date_to', 'contract_id.date_start')
    def get_anc(self):
        for record in self:
            if record.contract_id and record.date_to:
                debut = record.contract_id.date_start
                fin = record.date_to
                record.ancannee = relativedelta(fin, debut).years
                record.ancmois = relativedelta(fin, debut).months
    @api.depends('line_ids.total', 'worked_days_line_ids.number_of_days', 'input_line_ids.amount')
    def get_rub(self):
        for record in self:
            netp = 0
            for recordfil in record.line_ids:
                if recordfil.code == 'SBRUT':
                    record.brutp = recordfil.total
                if recordfil.code == 'NETI':
                    netp = netp + recordfil.total
                if recordfil.code == 'COTSAL':
                    record.chargesalp = recordfil.total
                if recordfil.code == 'COTPAT':
                    record.chargepatp = recordfil.total
                if recordfil.code == 'SITS':
                    record.itsp = recordfil.total
                if recordfil.code == 'NET':
                    record.snetp = recordfil.total
            record.netp = netp
            for recordfill in record.worked_days_line_ids:
                if recordfill.code == 'WORK100':
                    record.heuretp = recordfill.number_of_hours
            tothsup = 0
            for recordfilll in record.input_line_ids:
                if 'HSUP' in recordfilll.code:
                    tothsup = tothsup + recordfilll.amount
                if recordfilll.code == 'CONGEP':
                    record.congepp = recordfilll.amount
                record.heuresupp = tothsup
            record.congeacp = 2.5
            record.congerestp = 0

    @api.depends('brutp', 'netp', 'chargesalp', 'chargepatp', 'heuretp', 'heuresupp', 'congeacp', 'congepp',
                 'congerestp')
    def get_ruba(self):
        for record in self:
            # bula = self.env['hr.payslip'].search([('date_to','ilike',record.date_to[0:4]),('employee_id','=',record.employee_id.id)])
            bula = self.env['hr.payslip'].search(
                [('date_to', 'ilike', record.date_to.year), ('employee_id', '=', record.employee_id.id)])
            bruta = record.contract_id.bruti
            neta = record.contract_id.neti
            chargesala = record.contract_id.chargesali
            chargepata = record.contract_id.chargepati
            heureta = record.contract_id.heureti
            heuresupa = record.contract_id.heuresupi
            congeaca = record.contract_id.congeaci
            congepa = record.contract_id.congepi
            congeresta = 0
            for recordf in bula:
                bruta = bruta + recordf.brutp
                neta = neta + recordf.netp
                chargesala = chargesala + recordf.chargesalp
                chargepata = chargepata + recordf.chargepatp
                heureta = heureta + recordf.heuretp
                heuresupa = heuresupa + recordf.heuresupp
                congeaca = congeaca + recordf.congeacp
                congepa = congepa + recordf.congepp
                congeresta = congeaca - congepa
                if congeresta < 0:
                    congeresta = 0
            record.bruta = bruta
            record.neta = neta
            record.chargesala = chargesala
            record.chargepata = chargepata
            record.heureta = heureta
            record.heuresupa = heuresupa
            record.congeaca = congeaca
            record.congepa = congepa
            record.congeresta = congeresta
    ancannee = fields.Integer('Ancienneté années', compute='get_anc', store=True)
    ancmois = fields.Integer('Ancienneté mois', compute='get_anc', store=True)
    brutp = fields.Float('Brut Période', compute='get_rub', store=True)
    netp = fields.Float('Net imposable', compute='get_rub', store=True)
    snetp = fields.Float('Net', compute='get_rub', store=True)
    chargesalp = fields.Float('Charge salariale', compute='get_rub', store=True)
    chargepatp = fields.Float('Charge patronale', compute='get_rub', store=True)
    itsp = fields.Float('Impot traitement', compute='get_rub', store=True)
    heuretp = fields.Float('Heures travaillées', compute='get_rub', store=True)
    heuresupp = fields.Float('Heures sup', compute='get_rub', store=True)
    congeacp = fields.Float('Congés acquis', compute='get_rub', store=True)
    congepp = fields.Float('Congés pris', compute='get_rub', store=True)
    congerestp = fields.Float('Congés restant', compute='get_rub', store=True)
    bruta = fields.Float('Brut Année', compute='get_ruba', store=True)
    neta = fields.Float('Net imposable', compute='get_ruba', store=True)
    chargesala = fields.Float('Charge salariale', compute='get_ruba', store=True)
    chargepata = fields.Float('Charge patronale', compute='get_ruba', store=True)
    heureta = fields.Float('Heures travaillées', compute='get_ruba', store=True)
    heuresupa = fields.Float('Heures sup', compute='get_ruba', store=True)
    congeaca = fields.Float('Congés acquis', compute='get_ruba', store=True)
    congepa = fields.Float('Congés pris', compute='get_ruba', store=True)
    congeresta = fields.Float('Congés restant', compute='get_ruba', store=True)
    modep = fields.Selection([('Chèque', 'Chèque'), ('Virement', 'Virement'), ('Espèces', 'Espèces')], string='Mode de paiement', default='Chèque')
    datep = fields.Date('Date paiement')
    nbj = fields.Integer('Jours travaillés', default=30)

class Employee(models.Model):
    _name = "hr.employee"
    _description = "Employee"
    _inherit = "hr.employee"

    categorie = fields.Char('Catégorie')
    echelon = fields.Char('Echelon')
    secsoc = fields.Char('N° Sécurité sociale')

class HrPayslipRun(models.Model):
    _name = "hr.payslip.run"
    _description = "Lot de bulletin"
    _inherit = "hr.payslip.run"
    
    def convlettre(self,montant):
        return num2words(montant, lang='fr')
    @api.depends('slip_ids.line_ids.total')
    def centralise(self):
        rd1 = 0
        rd2 = 0
        rdn = 0
        indf = 0
        cotsal = 0
        cotpat = 0
        src = 0
        sits = 0
        srm = 0
        srmc = 0
        srmp = 0
        sav = 0
        for record in self:
            for recordfil in record.slip_ids:
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['BSB', 'BSS', 'NHA', 'BHS', 'BCP']:
                        rd1 = rd1 + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['BPANC', 'BPC', 'BPN', 'BPRA', 'BPA', 'BPE']:
                        rd2 = rd2 + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['SINF']:
                        indf = indf + recordfill.total
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['COTSAL']:
                        cotsal = cotsal + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['COTPAT']:
                        cotpat = round(cotpat + recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['SRC']:
                        src = src + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['SITS']:
                        sits = sits + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['RETACHAT']:
                        srm = srm + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['RETPHARMACIE']:
                        srmp = srmp + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['SRMC']:
                        srmc = srmc + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['SAV']:
                        sav = sav + round(recordfill.total, 0)
                for recordfill in recordfil.line_ids:
                    if recordfill.code in ['NET']:
                        rdn = rdn + (round(recordfill.total / 5, 0)) * 5
            rdc = rd1 + rd2 + indf
            cnsss = cotsal
            cnssp = cotpat
            itsc = sits
            rdd = src + srm + srmc + sav
            record.rd1 = rd1
            record.rd2 = rd2
            record.indf = indf
            record.cotsal = cotsal
            record.cotpat = cotpat
            record.src = src
            record.sits = sits
            record.srm = srm
            record.srmc = srmc
            record.srmp = srmp
            record.sav = sav
            record.rdc = rdc
            record.rdd = rdd
            record.rdn = rdn

    rd1 = fields.Float('Remunération base', compute='centralise', store=True)
    rd2 = fields.Float('Primes et gratifications', compute='centralise', store=True)
    indf = fields.Float('Indemnité forfaitaire', compute='centralise', store=True)
    cotsal = fields.Float('Cotisations salariales', compute='centralise', store=True)
    cotpat = fields.Float('Cotisations patronales', compute='centralise', store=True)
    src = fields.Float('Retenue CM', compute='centralise', store=True)
    sits = fields.Float('Impots traitement', compute='centralise', store=True)
    srm = fields.Float('Retenue Achat', compute='centralise', store=True)
    srmc = fields.Float('Retenue Achat Cafetariat', compute='centralise', store=True)
    srmp = fields.Float('Retenue Achat Pharmacie', compute='centralise', store=True)
    sav = fields.Float('Avance et acompte', compute='centralise', store=True)
    rdc = fields.Float('Remunération directe crediteur', compute='centralise', store=True)
    rdd = fields.Float('Remunération directe debiteur', compute='centralise', store=True)
    rdn = fields.Float('Remunération nette', compute='centralise', store=True)
