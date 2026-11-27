FROM odoo:17.0

USER root
COPY deploy/huggingface/odoo/start_odoo.sh /usr/local/bin/start_odoo.sh
RUN chmod +x /usr/local/bin/start_odoo.sh && mkdir -p /var/lib/odoo && chown -R odoo:odoo /var/lib/odoo
USER odoo

EXPOSE 7860
CMD ["/usr/local/bin/start_odoo.sh"]
