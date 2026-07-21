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
            'montant_financier': float(post.get('montant_propose', 0)),
            'delai_execution': int(post.get('delai_execution', 0)),
            'note_soumission': post.get('note_soumission', ''),
            'date_reception': fields.Datetime.now(),
            'ip_soumission': request.httprequest.remote_addr,
        })

        # Pièces jointes
        attachments = request.httprequest.files.getlist('documents')
        for f in attachments:
            attachment = request.env['ir.attachment'].sudo().create({
            'name': f"{offre.fournisseur_id.name} - {f.filename}",  # Avec nom du fournisseur
            'datas': base64.b64encode(f.read()),
            'res_model': 'resade.marche',
            'res_id': ligne.marche_id.id,
        })
        # Ajouter au champ pj_offres du marché
        ligne.marche_id.sudo().write({'pj_offres': [(4, attachment.id)]})

        ligne.write({
            'state': 'offre_recue',
            'offre_id': offre.id,
            'offre_recue': True,
            'date_reception_offre': fields.Date.today(),
        })
        # jsjsjsj
        # DEBUG SIMPLE SANS SQL
        marche = ligne.marche_id.sudo()
        print("=== DEBUG PJ OFFRES ===")
        print("IDs dans pj_offres:", marche.pj_offres.ids)
        print("Nombre de PJ:", len(marche.pj_offres))
        for pj in marche.pj_offres:
            print(f"  - {pj.id}: {pj.name}")
        print("=== FIN DEBUG ===")


        return request.render('resade_marche.confirmation_soumission', {
            'offre': offre,
            'marche': ligne.marche_id,
        })
    
    # ─────────────────────────────────────────
    # APPEL D'OFFRES OUVERT (token public)
    # ─────────────────────────────────────────


    @http.route('/marche/aoo/<string:token>', type='http', auth='public', website=True)
    def afficher_aoo(self, token, **kwargs):
        """Affiche le formulaire public pour un Appel d'Offres Ouvert."""
        marche = request.env['resade.marche'].sudo().search([
            ('token_public', '=', token)
        ], limit=1)

        if not marche:
            return "Appel d'offres introuvable."

        if marche.state not in ('ao_lance', 'depouillement'):
            return "Cet appel d'offres est fermé."

        return request.render('resade_marche.formulaire_aoo', {
            'marche': marche,
            'token': token,
        })

    @http.route('/marche/aoo/<string:token>/soumettre', type='http',
            auth='public', website=True, methods=['POST'], csrf=True)
    def soumettre_aoo(self, token, **post):
        marche = request.env['resade.marche'].sudo().search([
            ('token_public', '=', token)
        ], limit=1)

        if not marche or marche.state not in ('ao_lance', 'depouillement'):
            return "Appel d'offres fermé."

        fournisseur_id = post.get('fournisseur_id')
        nom_fournisseur = post.get('nom_fournisseur', '')
        email = post.get('email', '')

        # Si le fournisseur existe déjà
        if fournisseur_id and fournisseur_id != 'new':
            fournisseur = request.env['resade.fournisseur'].sudo().browse(int(fournisseur_id))
        else:
            # Créer un nouveau fournisseur
            fournisseur = request.env['resade.fournisseur'].sudo().create({
                'name': nom_fournisseur,
                'email': email,
            })

        offre = request.env['resade.marche.offre'].sudo().create({
            'marche_id': marche.id,
            'fournisseur_id': fournisseur.id,
            'montant_financier': float(post.get('montant_propose', 0)),
            'delai_execution': int(post.get('delai_execution', 0)),
            'date_reception': fields.Datetime.now(),
        })

        # Pièces jointes
        attachments = request.httprequest.files.getlist('documents')
        for f in attachments:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': f"{fournisseur.name} - {f.filename}",
                'datas': base64.b64encode(f.read()),
                'res_model': 'resade.marche',
                'res_id': marche.id,
            })
            marche.sudo().write({'pj_offres': [(4, attachment.id)]})

        return request.render('resade_marche.confirmation_aoo', {
            'marche': marche,
        })



# from odoo import http

# class TestPortail(http.Controller):

#     @http.route('/test-resade', type='http', auth='public', website=True)
#     def test(self):
#         return "TEST RESADE OK - Le contrôleur fonctionne !"