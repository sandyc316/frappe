# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.controller import DocListController
from frappe.website.utils import cleanup_page_name
from frappe.utils import now

from frappe.website.doctype.website_route.website_route import add_to_sitemap, update_sitemap, remove_sitemap

def call_website_generator(bean, method, *args, **kwargs):
	getattr(WebsiteGenerator(bean.doc, bean.doclist), method)(*args, **kwargs)

class WebsiteGenerator(DocListController):
	def autoname(self):
		self.name = self.get_page_name()
		self.append_number_if_name_exists()

	def set_page_name(self):
		"""set page name based on parent page_name and title"""
		page_name = cleanup_page_name(self.get_page_title())

		if self.is_new():
			self.set(self.website_template.page_name_field, page_name)
		else:
			frappe.db.set(self, self.website_template.page_name_field, page_name)
			
		return page_name

	def get_parent_website_route(self):
		return self.parent_website_route

	def setup_generator(self):
		if not hasattr(self, "website_template"):
			self.website_template = frappe.db.get_values("Website Template", 
				{"ref_doctype": self.doctype}, "*")[0]

	def on_update(self):
		self.update_sitemap()
		if getattr(self, "save_versions", False):
			frappe.add_version(self.doclist)
		
	def after_rename(self, olddn, newdn, merge):
		frappe.db.sql("""update `tabWebsite Route`
			set docname=%s where ref_doctype=%s and docname=%s""", (newdn, self.doctype, olddn))
		
		if merge:
			self.setup_generator()
			remove_sitemap(ref_doctype=self.doctype, docname=olddn)
		
	def on_trash(self):
		self.setup_generator()
		remove_sitemap(ref_doctype=self.doctype, docname=self.name)
		
	def update_sitemap(self):
		self.setup_generator()
		
		if self.website_template.condition_field and \
			not self.get(self.website_template.condition_field):
			# condition field failed, remove and return!
			remove_sitemap(ref_doctype=self.doctype, docname=self.name)
			return
				
		self.add_or_update_sitemap()
		
	def add_or_update_sitemap(self):
		page_name = self.get_page_name()
		
		existing_site_map = frappe.db.get_value("Website Route", {"ref_doctype": self.doctype,
			"docname": self.name})
		
		if self.modified:
			lastmod = frappe.utils.get_datetime(self.modified).strftime("%Y-%m-%d")
		else:
			lastmod = now()
		
		opts = frappe._dict({
			"page_or_generator": "Generator",
			"ref_doctype":self.doctype, 
			"idx": self.idx,
			"docname": self.name,
			"page_name": page_name,
			"link_name": self.website_template.name,
			"lastmod": lastmod,
			"parent_website_route": self.get_parent_website_route(),
			"page_title": self.get_page_title(),
			"public_read": 1 if not self.website_template.no_sidebar else 0
		})

		self.update_permissions(opts)
		
		if existing_site_map:
			idx = update_sitemap(existing_site_map, opts)
		else:
			idx = add_to_sitemap(opts)

		if idx!=None and self.idx != idx:
			frappe.db.set(self, "idx", idx)			
	
	def update_permissions(self, opts):
		if self.meta.get_field("public_read"):
			opts.public_read = self.public_read
			opts.public_write = self.public_write
		else:
			opts.public_read = 1
	
	def get_page_name(self):
		page_name = self._get_page_name()
		if not page_name:
			page_name = self.set_page_name()
			
		return self._get_page_name()
		
	def _get_page_name(self):
		self.setup_generator()
		if self.meta.has_field(self.website_template.page_name_field):
			return self.get(self.website_template.page_name_field)
		else:
			return cleanup_page_name(self.get_page_title())
		
	def get_page_title(self):
		return self.title or (self.name.replace("-", " ").replace("_", " ").title())
