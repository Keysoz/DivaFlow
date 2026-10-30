// Party Statement — filters and report actions.
//
// The data comes from the Script Report in party_statement.py. The filters
// below are the only public inputs; the server validates them again.

(function () {
const PARTY_STATEMENT_FORMAT = "Party Statement Print";
const PARTY_STATEMENT_METHOD =
	"custom_reports.custom_reports.report.party_statement.party_statement.get_fiscal_year_start";

frappe.query_reports["Party Statement"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company") || frappe.defaults.get_default("company"),
			on_change: function () {
				// Keep the period aligned with the selected company's fiscal year.
				const report = frappe.query_report;
				if (!report) return;
				const company = report.get_filter_value("company");
				if (!company) return;
				frappe
					.xcall(PARTY_STATEMENT_METHOD, { company })
					.then((start) => report.set_filter_value("from_date", start));
			},
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Select",
			options: "Customer\nSupplier",
			reqd: 1,
			default: "Customer",
			on_change: function () {
				// A customer name is not a supplier name; clear the dependent field.
				const report = frappe.query_report;
				if (report) report.set_filter_value("party", "");
			},
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "Dynamic Link",
			reqd: 1,
			// v16 resolves a Dynamic Link filter through get_options, not a
			// fieldname in options, so the select above can change it live.
			get_options: function () {
				return frappe.query_report.get_filter_value("party_type");
			},
			get_query: function () {
				// Do not offer disabled parties.
				return { filters: { disabled: 0 } };
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.year_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "show_cancelled",
			label: __("Show Cancelled"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "combine",
			label: __("Combine same-name Customer / Supplier"),
			fieldtype: "Check",
			default: 1,
			description: __(
				"When a Customer and a Supplier share this name, show both ledgers as one net statement."
			),
		},
		{
			fieldname: "letter_head",
			label: __("Letter Head"),
			fieldtype: "Link",
			options: "Letter Head",
			get_query: function () {
				return { filters: { disabled: 0 } };
			},
		},
	],

	onload: function (report) {
		// v16 has no Report.default_print_format column, so the PDF dialog would
		// otherwise fall back to the grid. Set it on the loaded report document
		// (client-side only) and add a one-click print button.
		report.report_doc.default_print_format = PARTY_STATEMENT_FORMAT;

		report.page.add_inner_button(__("Print Statement"), function () {
			if (!report.data || !report.data.length) {
				frappe.msgprint(__("There is nothing to print for the selected filters."));
				return;
			}
			const dialog = frappe.ui.get_print_settings(
				false,
				(settings) => report.print_report(settings),
				report.report_doc.letter_head,
				report.get_visible_columns(),
				true,
				__("Print Settings"),
				PARTY_STATEMENT_FORMAT
			);
			// The statement is designed for A4 portrait; v16's report print
			// dialog defaults to landscape, so preselect portrait.
			if (dialog && dialog.set_value) {
				dialog.set_value("orientation", "Portrait");
			}
		});

		// Replace the placeholder From Date with the actual fiscal year start.
		const company = report.get_filter_value("company");
		if (company) {
			frappe.xcall(PARTY_STATEMENT_METHOD, { company }).then((start) => {
				if (start) report.set_filter_value("from_date", start);
			});
		}
	},
};
})();
