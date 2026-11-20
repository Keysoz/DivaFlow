/* Diva Desk: the Supplier and Customer quick entries (DEC-107).
 *
 * ERPNext builds both dialogs from `ContactAddressQuickEntryForm`: the party
 * fields plus an inline primary contact and primary address. The shop does not
 * keep an email, a postal code or a state for a party here, and every party is
 * in Cairo, Egypt, so the dialog drops those three inputs and pre-fills the
 * city and the country. The city is Arabic because it is stored data, not a UI
 * string; the country is the `Country` record name.
 *
 * Loaded through `app_include_js`. ERPNext core and POS Next are never edited.
 * If an upgrade renames the base class (or its `get_variant_fields`), the
 * override steps aside and the stock Add Supplier/Add Customer dialog still
 * works: a quick-entry dialog must never be broken by this file.
 */
(function () {
	"use strict";

	const CITY = "القاهرة";
	const COUNTRY = "Egypt";
	const DROPPED_FIELDS = new Set(["email_address", "pincode", "state"]);

	function with_party_defaults(base) {
		return class extends base {
			get_variant_fields() {
				const fields = super.get_variant_fields().filter(
					(df) => !DROPPED_FIELDS.has(df.fieldname)
				);
				for (const df of fields) {
					if (df.fieldname === "city" && !df.default) df.default = CITY;
					if (df.fieldname === "country_address" && !df.default) df.default = COUNTRY;
				}
				return fields;
			}
		};
	}

	const base = frappe.ui.form && frappe.ui.form.ContactAddressQuickEntryForm;
	if (typeof base !== "function" || typeof base.prototype.get_variant_fields !== "function") {
		// ERPNext changed shape; keep its dialog untouched.
		return;
	}

	const DivaContactAddressQuickEntry = with_party_defaults(base);
	frappe.ui.form.SupplierQuickEntryForm = DivaContactAddressQuickEntry;
	frappe.ui.form.CustomerQuickEntryForm = DivaContactAddressQuickEntry;
})();
