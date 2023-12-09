msg_e_disco_no_montado = "El disco externo no se ha montado correctamente"
msg_e_disco_no_preparado = "NO SE HA REALIZADO LA COPIA!!!! El disco con el numero de serie {} no esta preparado"
msg_e_disco_no_vinculado = "no se ha podido desvincular el disco por el siguiente motivo:"
msg_e_disco_vinculado = "no se ha realizado la vinculacion el disco por el siguiente motivo:"
msg_i_luks_open = "Abriendo canal cifrado en disco {} ({}) como backup-externo"
msg_e_sync_error = "Se ha produccido un error en la sincronizacion de {}"
msg_mail_body_warn = 'La copia ha finalizado con advertencias, informe a sistemas si es necesario. <br><br> Advertencias: <br><br> {}'
msg_mail_sbj_warn = 'HAY ADVERTENCIAS. Consulte a sistemas si es necesario, antes de cambiar el disco'
msg_e_no_disco = 'No se encuentra ningun disco que contenga alguna de las series proporcionadas'
msg_w_canal_abierto = 'El canal cifrado del dispositivo {} se ha encontrado abierto de una operacion anterior, pero se ha cerrado con exito'

config_template = {'config': {
	'last_device': '',
	'vmc': False,
	'empresa': '',
	'item': '',
	'dom0': '',
	'dom0_backup': 'backup.hvm',
	'disco_interno': '',
	'discos': [],
	'email_smtp': '',
	'email_login': '',
	'email_from': '',
	'email_responsables': '',
	'smart': '',
	'luks_phrase': '',
	'luks_phrase_url': '',
	'luks_phrase_user': '',
	'luks_phrase_pass': ''},
	'tareas': []}

warnings = []

dialogrc = "aspect = 0\n" \
           "separate_widget = \"\"\n" \
           "tab_len = 0\n" \
           "visit_items = OFF\n" \
           "use_shadow = OFF\n" \
           "use_colors = ON\n" \
           "screen_color = (WHITE,DEFAULT,OFF)\n" \
           "shadow_color = (WHITE,WHITE,OFF)\n" \
           "dialog_color = (WHITE,BLACK,OFF)\n" \
           "title_color = (GREEN,BLACK,OFF)\n" \
           "border_color = (WHITE,BLACK,OFF)\n" \
           "button_active_color = (BLACK,YELLOW,OFF)\n" \
           "button_inactive_color = (WHITE,BLACK,OFF)\n" \
           "button_key_active_color = (BLACK,GREEN,OFF)\n" \
           "button_key_inactive_color = (RED,BLACK,OFF)\n" \
           "button_label_active_color = (BLACK,YELLOW,OFF)\n" \
           "button_label_inactive_color = (WHITE,BLACK,OFF)\n" \
           "inputbox_color = (WHITE,BLACK,OFF)\n" \
           "inputbox_border_color = (BLACK,BLACK,OFF)\n" \
           "searchbox_color = (WHITE,BLACK,OFF)\n" \
           "searchbox_title_color = (GREEN,BLACK,OFF)\n" \
           "position_indicator_color = (GREEN,BLACK,OFF)\n" \
           "menubox_color = (BLACK,BLACK,OFF)\n" \
           "menubox_border_color = (BLACK,BLACK,OFF)\n" \
           "item_color = (WHITE,BLACK,OFF)\n" \
           "item_selected_color = (BLACK,GREEN,OFF)\n" \
           "tag_color = (BLUE,BLACK,OFF)\n" \
           "tag_selected_color = (BLACK,GREEN,OFF)\n" \
           "tag_key_color = (YELLOW,BLACK,OFF)\n" \
           "tag_key_selected_color = (BLACK,GREEN,OFF)\n" \
           "check_color = (WHITE,BLACK,OFF)\n" \
           "check_selected_color = (BLACK,GREEN,OFF)\n" \
           "uarrow_color = (GREEN,BLACK,OFF)\n" \
           "darrow_color = (GREEN,BLACK,OFF)\n" \
           "itemhelp_color = (BLACK,WHITE,OFF)\n" \
           "form_active_text_color = (BLACK,BLUE,OFF)\n" \
           "form_text_color = (WHITE,BLACK,OFF)\n" \
           "form_item_readonly_color = (BLACK,WHITE,OFF)\n"
