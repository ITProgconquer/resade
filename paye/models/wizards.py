# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from operator import ne
from threading import Condition
from odoo import models, fields, api, _
import re
from odoo.exceptions import UserError, ValidationError

class PaieLivrePaiexlsx(models.AbstractModel):
    _name = "report.paye.report_livrepaiexlsx"
    _inherit="report.report_xlsx.abstract"
    _description = "Livre de paie excel"
    
    def _get_report_values(self, docids, data=None):
        return{
            "docids":docids,
            "lui":docids.ids,
        }

    def generate_xlsx_report(self, workbook, data, docids):
        lines=self._get_report_values(docids)
        selected_records=self.env['hr.payslip.run'].browse(lines['lui'])
        force=[]
        for record in selected_records:
            val={
                "id":record.id,
                "nom":record.name,
                "debut":record.date_start,
                "fin":record.date_end,
                "slip_ids":record.slip_ids,
            }
            force.append(val)
        bolth    = workbook.add_format({'bold': 1,'align': 'center','fg_color': '#B9FFFF','border': 1})
        boltd    = workbook.add_format({'border': 1})
        my_format= workbook.add_format({'border': 1,'num_format':'dd/mm/yyyy'})
        boltdsep = workbook.add_format({'border': 1,'num_format':'# ##0'})
        identbo  = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','fg_color': 'orange'})

        for lot in force:
            worksheet = workbook.add_worksheet('Journal de paie '+lot['nom'])
            worksheet.set_column(0, 4, 15)
            col=0
            row=1
            worksheet.merge_range(0, col, 0, col+4, 'Journal de paie '+lot['nom'], identbo)

            # ---- EN-TÊTES ----
            worksheet.write(row, col + 0,  'Matricule',       bolth)
            worksheet.write(row, col + 1,  'Nom Prénoms',     bolth)
            worksheet.write(row, col + 2,  'Charges',         bolth)
            worksheet.write(row, col + 3,  'Début de contrat',bolth)
            worksheet.write(row, col + 4,  'Emploi occupé',   bolth)
            worksheet.write(row, col + 5,  'Salaire de base', bolth)
            worksheet.write(row, col + 6,  'Sursalaire',      bolth)
            worksheet.write(row, col + 7,  'Ind. Logement',   bolth)
            worksheet.write(row, col + 8,  'Ind. Transport',  bolth)
            worksheet.write(row, col + 9,  'Ind. Fonction',   bolth)
            worksheet.write(row, col + 10, 'Prime Anc',       bolth)
            worksheet.write(row, col + 11, 'Salaire brut',    bolth)
            worksheet.write(row, col + 12, 'CNSS 5.5%',       bolth)
            worksheet.write(row, col + 13, 'CNSS 16%',        bolth)
            worksheet.write(row, col + 14, 'IUTS',            bolth)
            worksheet.write(row, col + 15, 'TPA',             bolth)
            worksheet.write(row, col + 16, 'FSP 1%',          bolth)  # NOUVEAU
            worksheet.write(row, col + 17, 'Retenue Mutuelle',bolth)  # NOUVEAU
            worksheet.write(row, col + 18, 'Autres retenues', bolth)
            worksheet.write(row, col + 19, 'Net à Payer',     bolth)
            worksheet.write(row, col + 20, 'Jr Trav',         bolth)

            # ---- INITIALISATIONS TOTAUX ----
            totsbase = totsursal = totindlog = totindtrans = totindfonc = totpanc = totsbrut = 0
            totcnss5 = totcnss16 = totiuts = tottpa = totfsp = totretmut = totatret = totnet = 0

            # ---- LIGNES PAR EMPLOYÉ ----
            for bul in lot['slip_ids'].sorted(key=lambda line: line.employee_id.name):
                sbase = sursal = indlog = indtrans = indfonc = panc = sbrut = 0
                cnss5 = cnss16 = iuts = tpa = fsp = retmut = atret = net = 0

                for ls in bul.line_ids:
                    if ls.code == 'SBASE':
                        sbase  = round(ls.total, 0); totsbase   += sbase
                    if ls.code == 'SURSAL':
                        sursal = round(ls.total, 0); totsursal  += sursal
                    if ls.code == 'INDLOG':
                        indlog = round(ls.total, 0); totindlog  += indlog
                    if ls.code == 'INDTRANS':
                        indtrans = round(ls.total, 0); totindtrans += indtrans
                    if ls.code == 'INDFONC':
                        indfonc = round(ls.total, 0); totindfonc += indfonc
                    if ls.code == 'PANC':
                        panc   = round(ls.total, 0); totpanc    += panc
                    if ls.code == 'SBRUT':
                        sbrut  = round(ls.total, 0); totsbrut   += sbrut
                    if ls.code == 'CNSS':
                        cnss5  = round(ls.total, 0); totcnss5   += cnss5
                    if ls.code == 'CP':
                        cnss16 = round(ls.total, 0); totcnss16  += cnss16
                    if ls.code == 'IUTS':
                        iuts   = round(ls.total, 0); totiuts    += iuts
                    if ls.code == 'TPA':
                        tpa    = round(ls.total, 0); tottpa     += tpa
                    if ls.code == 'FSP':
                        fsp    = round(ls.total, 0); totfsp     += fsp
                    if ls.code == 'RETMUT':
                        retmut = round(ls.total, 0); totretmut  += retmut
                    if ls.code == 'ATRET':
                        atret  = round(ls.total, 0); totatret   += atret
                    if ls.code == 'NET':
                        net    = round(ls.total, 0); totnet     += net

                row += 1
                worksheet.write(row, col + 0,  bul.employee_id.identification_id, boltd)
                worksheet.write(row, col + 1,  bul.employee_id.name,              boltd)
                worksheet.write(row, col + 2,  bul.employee_id.children,          boltd)
                worksheet.write(row, col + 3,  bul.contract_id.date_start,        my_format)
                worksheet.write(row, col + 4,  bul.employee_id.job_id.name,       boltd)
                worksheet.write(row, col + 5,  sbase,   boltdsep)
                worksheet.write(row, col + 6,  sursal,  boltdsep)
                worksheet.write(row, col + 7,  indlog,  boltdsep)
                worksheet.write(row, col + 8,  indtrans,boltdsep)
                worksheet.write(row, col + 9,  indfonc, boltdsep)
                worksheet.write(row, col + 10, panc,    boltdsep)
                worksheet.write(row, col + 11, sbrut,   boltdsep)
                worksheet.write(row, col + 12, cnss5,   boltdsep)
                worksheet.write(row, col + 13, cnss16,  boltdsep)
                worksheet.write(row, col + 14, iuts,    boltdsep)
                worksheet.write(row, col + 15, tpa,     boltdsep)
                worksheet.write(row, col + 16, fsp,     boltdsep)   # NOUVEAU
                worksheet.write(row, col + 17, retmut,  boltdsep)   # NOUVEAU
                worksheet.write(row, col + 18, atret,   boltdsep)
                worksheet.write(row, col + 19, net,     boltdsep)
                worksheet.write(row, col + 20, bul.nbj, boltd)

            # ---- LIGNE TOTAL ----
            row += 1
            worksheet.write(row, col + 0,  "TOTAL",      boltd)
            worksheet.write(row, col + 1,  "",           boltd)
            worksheet.write(row, col + 2,  "",           boltd)
            worksheet.write(row, col + 3,  "",           my_format)
            worksheet.write(row, col + 4,  "",           boltd)
            worksheet.write(row, col + 5,  totsbase,     boltdsep)
            worksheet.write(row, col + 6,  totsursal,    boltdsep)
            worksheet.write(row, col + 7,  totindlog,    boltdsep)
            worksheet.write(row, col + 8,  totindtrans,  boltdsep)
            worksheet.write(row, col + 9,  totindfonc,   boltdsep)
            worksheet.write(row, col + 10, totpanc,      boltdsep)
            worksheet.write(row, col + 11, totsbrut,     boltdsep)
            worksheet.write(row, col + 12, totcnss5,     boltdsep)
            worksheet.write(row, col + 13, totcnss16,    boltdsep)
            worksheet.write(row, col + 14, totiuts,      boltdsep)
            worksheet.write(row, col + 15, tottpa,       boltdsep)
            worksheet.write(row, col + 16, totfsp,       boltdsep)    # NOUVEAU
            worksheet.write(row, col + 17, totretmut,    boltdsep)    # NOUVEAU
            worksheet.write(row, col + 18, totatret,     boltdsep)
            worksheet.write(row, col + 19, totnet,       boltdsep)
            worksheet.write(row, col + 20, "",           boltd)


class PaieIutsxlsx(models.AbstractModel):
    _name = "report.paye.report_iutsxlsx"
    _inherit="report.report_xlsx.abstract"
    _description = "IUTS excel"
    
    def _get_report_values(self, docids, data=None):
        return{
            "docids":docids,
            "lui":docids.ids,
        }
    def generate_xlsx_report(self, workbook, data, docids):
        lines=self._get_report_values(docids)
        selected_records=self.env['hr.payslip.run'].browse(lines['lui'])
        force=[]
        for record in selected_records:
            val={
                "id":record.id,
                "nom":record.name,
                "debut":record.date_start,
                "fin":record.date_end,
                "slip_ids":record.slip_ids,
            }
            force.append(val)
        bolth    = workbook.add_format({'bold': 1,'align': 'center','fg_color': '#B9FFFF','border': 1})
        boltd    = workbook.add_format({'border': 1})
        my_format= workbook.add_format({'border': 1,'num_format':'dd/mm/yyyy'})
        boltdsep = workbook.add_format({'border': 1,'num_format':'# ##0'})
        identbo  = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','fg_color': 'orange'})
        for lot in force:
            worksheet = workbook.add_worksheet('ETAT IUTS et TPA '+lot['nom'])
            worksheet.set_column(0, 4, 15)
            col=0
            row=1
            worksheet.merge_range(0, col,0,col+4, 'ETAT IUTS et TPA  '+lot['nom'],identbo)
            worksheet.write(row, col,     'Matricule',      bolth)
            worksheet.write(row, col + 1, 'Nom Prénoms',    bolth)
            worksheet.write(row, col + 2, 'Salaire brut',   bolth)
            worksheet.write(row, col + 3, 'Total imposable',bolth)
            worksheet.write(row, col + 4, 'Charges',        bolth)
            worksheet.write(row, col + 5, 'IUTS dû',        bolth)
            worksheet.write(row, col + 6, 'TPA dû',         bolth)
            totsbrut = totsi = totiuts = tottpa = 0
            for bul in lot['slip_ids'].sorted(key=lambda line: line.employee_id.name):
                sbrut=si=iuts=tpa=0
                for ls in bul.line_ids:
                    if ls.code == 'SBRUT':
                       sbrut = round(ls.total,0); totsbrut+=sbrut 
                    if ls.code == 'BIUTS':
                       si = round(ls.total,0); totsi+=si 
                    if ls.code == 'IUTS':
                       iuts = round(ls.total,0); totiuts+=iuts
                    if ls.code == 'TPA':
                       tpa = round(ls.total,0); tottpa+=tpa 
                row+=1
                worksheet.write(row, col,   bul.employee_id.identification_id, boltd)
                worksheet.write(row, col+1, bul.employee_id.name,              boltd)
                worksheet.write(row, col+2, sbrut,                             boltdsep)
                worksheet.write(row, col+3, si,                                boltdsep)
                worksheet.write(row, col+4, bul.employee_id.children,          boltd)
                worksheet.write(row, col+5, iuts,                              boltdsep)
                worksheet.write(row, col+6, tpa,                               boltdsep)
        row+=1
        worksheet.write(row, col,   "TOTAL", boltd)
        worksheet.write(row, col+1, "",       boltd)
        worksheet.write(row, col+2, totsbrut, boltdsep)
        worksheet.write(row, col+3, totsi,    boltdsep)
        worksheet.write(row, col+4, "",       boltd)
        worksheet.write(row, col+5, totiuts,  boltdsep)
        worksheet.write(row, col+6, tottpa,   boltdsep)


class PaieCNSSxlsx(models.AbstractModel):
    _name = "report.paye.report_cnssxlsx"
    _inherit="report.report_xlsx.abstract"
    _description = "Etat CNSS excel"
    
    def _get_report_values(self, docids, data=None):
        return{
            "docids":docids,
            "lui":docids.ids,
        }
    def generate_xlsx_report(self, workbook, data, docids):
        lines=self._get_report_values(docids)
        selected_records=self.env['hr.payslip.run'].browse(lines['lui'])
        force=[]
        for record in selected_records:
            val={
                "id":record.id,
                "nom":record.name,
                "debut":record.date_start,
                "fin":record.date_end,
                "slip_ids":record.slip_ids,
            }
            force.append(val)
        bolth    = workbook.add_format({'bold': 1,'align': 'center','fg_color': '#B9FFFF','border': 1})
        boltd    = workbook.add_format({'border': 1, 'align': 'left'})
        my_format= workbook.add_format({'border': 1,'num_format':'dd/mm/yyyy'})
        boltdsep = workbook.add_format({'border': 1,'num_format':'# ##0'})
        identbo  = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','fg_color': 'orange'})
        for lot in force:
            worksheet = workbook.add_worksheet(lot['nom'])
            worksheet.set_column(0, 6, 15)
            col = 0
            row = 1
            worksheet.merge_range(0, col, 0, col + 9, lot['nom'], identbo)
            worksheet.write(row, col,     'N°',                                  bolth)
            worksheet.write(row, col + 1, 'Nom Prénoms',                         bolth)
            worksheet.write(row, col + 2, 'Date de naissance',                   bolth)
            worksheet.write(row, col + 3, 'N° d\'immatriculation C.N.S.S',       bolth)
            worksheet.write(row, col + 4, 'RENUMERATIONS soumises à côtisations',bolth)
            worksheet.write(row, col + 5, 'CNSS Employé',                        bolth)
            worksheet.write(row, col + 6, 'CNSS Employeur',                      bolth)
            worksheet.merge_range(row, col + 7, row, col + 8, 'Périodes',        bolth)
            worksheet.write(row + 1, col + 7, 'DU',                              bolth)
            worksheet.write(row + 1, col + 8, 'AU',                              bolth)
            worksheet.write(row, col + 9, 'Observations',                        bolth)
            totbcnss = 0
            for idx, bul in enumerate(lot['slip_ids'].sorted(key=lambda line: line.employee_id.name), start=1):
                lbcnss = bul.line_ids.filtered(lambda l:l.code=='BCNSS')
                bcnss = 0
                if lbcnss:
                   bcnss = round(lbcnss[0].total,0) 
                totbcnss+=bcnss
                row += 1
                worksheet.write(row, col,     idx,                                         boltd)
                worksheet.write(row, col + 1, bul.employee_id.name,                        boltd)
                worksheet.write(row, col + 2, bul.employee_id.birthday,                    my_format)
                worksheet.write(row, col + 3, bul.employee_id.ssnid,                       boltd)
                worksheet.write(row, col + 4, bcnss if lbcnss else '',                     boltdsep)
                worksheet.write(row, col + 5, round(bcnss*5.5/100,0) if lbcnss else '',    boltdsep)
                worksheet.write(row, col + 6, round(bcnss*16/100,0) if lbcnss else '',     boltdsep)
                if idx == 1:
                    worksheet.write(row, col + 7, lot['debut'], my_format)
                    worksheet.write(row, col + 8, lot['fin'],   my_format)
                else:
                    worksheet.write(row, col + 7, 'Période', workbook.add_format({'align': 'center', 'border': 1}))
                    worksheet.write(row, col + 8, 'Entière', workbook.add_format({'align': 'center', 'border': 1}))
                worksheet.write(row, col + 9, '', boltd)
            row += 1
            worksheet.write(row, col,     "TOTAL",                       boltd)
            worksheet.write(row, col + 1, "",                             boltd)
            worksheet.write(row, col + 2, "",                             my_format)
            worksheet.write(row, col + 3, "",                             boltd)
            worksheet.write(row, col + 4, totbcnss,                      boltdsep)
            worksheet.write(row, col + 5, round(totbcnss*5.5/100,0),     boltdsep)
            worksheet.write(row, col + 6, round(totbcnss*16/100,0),      boltdsep)
            worksheet.write(row, col + 7, 'Période', workbook.add_format({'align': 'center', 'border': 1}))
            worksheet.write(row, col + 8, 'Entière', workbook.add_format({'align': 'center', 'border': 1}))
            worksheet.write(row, col + 9, '', boltd)
