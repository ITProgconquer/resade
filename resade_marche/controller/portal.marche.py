# controllers/portal_marche.py
from odoo import http, fields
from odoo.http import request
import base64


class MarcheConsultationPortal(http.Controller):

    @http.route('/marche/consultation/<string:token>', type='http', auth='public', website=True)
    def afficher_formulaire(self, token, **kwargs):
        """Affiche le formulaire de dépôt d'offre pour le fournisseur invité."""
        ligne = request.env['resade.marche.liste.courte'].sudo().search([
            ('token', '=', token)
        ], limit=1)

        if not ligne:
            return request.render('resade_marche.token_invalide')

        if ligne.marche_id.state not in ('ao_lance', 'depouillement'):
            return request.render('resade_marche.consultation_fermee')

        if ligne.marche_id.date_limite_soumission and \
           fields.Date.today() > ligne.marche_id.date_limite_soumission:
            return request.render('resade_marche.date_limite_depassee')

        if ligne.state == 'offre_recue':
            return request.render('resade_marche.offre_deja_soumise')

        return request.render('resade_marche.formulaire_offre', {
            'ligne': ligne,
            'marche': ligne.marche_id,
        })

    @http.route('/marche/consultation/<string:token>/soumettre', type='http',
                auth='public', website=True, methods=['POST'], csrf=True)
    def soumettre_offre(self, token, **post):
        """Réceptionne la soumission d'offre du fournisseur."""
        ligne = request.env['resade.marche.liste.courte'].sudo().search([
            ('token', '=', token)
        ], limit=1)

        if not ligne:
            return request.render('resade_marche.token_invalide')

        if ligne.marche_id.state not in ('ao_lance', 'depouillement'):
            return request.render('resade_marche.consultation_fermee')

        if ligne.marche_id.date_limite_soumission and \
           fields.Date.today() > ligne.marche_id.date_limite_soumission:
            return request.render('resade_marche.date_limite_depassee')

        # Créer l'offre
        offre = request.env['resade.marche.offre'].sudo().create({
            'marche_id': ligne.marche_id.id,
            'fournisseur_id': ligne.fournisseur_id.id,
            'montant_propose': float(post.get('montant_propose', 0)),
            'delai_execution': int(post.get('delai_execution', 0)),
            'note_soumission': post.get('note_soumission', ''),
            'date_reception': fields.Datetime.now(),
            'ip_soumission': request.httprequest.remote_addr,
        })

        # Pièces jointes
        attachments = request.httprequest.files.getlist('documents')
        for f in attachments:
            request.env['ir.attachment'].sudo().create({
                'name': f.filename,
                'datas': base64.b64encode(f.read()),
                'res_model': 'resade.marche.offre',
                'res_id': offre.id,
            })

        ligne.write({
            'state': 'offre_recue',
            'offre_id': offre.id,
            'offre_recue': True,
            'date_reception_offre': fields.Date.today(),
        })

        return request.render('resade_marche.confirmation_soumission', {
            'offre': offre,
            'marche': ligne.marche_id,
        })