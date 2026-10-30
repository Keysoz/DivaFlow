/* Diva Desk - keyboard, focus and workflow layer (DEC-85/86/87/88).
 *
 * Loaded through `app_include_js` by the `diva_desk` app. Everything that
 * touches permissions, money, stock or payments lives on the server in
 * `diva_guard.desk_api`; this file only moves the cursor and opens dialogs.
 *
 * Purchase Receipt : supplier -> accepted warehouse -> items, Add New Item
 *                    (EAN-13 generation, label print), Print after submit.
 * Sales Invoice    : customer -> item, Pay (full or partial, Cash by default),
 *                    Print after submit and after pay. Nothing is automatic.
 * Shortcuts        : F1 help, F2 party, F3 item, F8 pay, F9 print,
 *                    Ctrl+S save, Ctrl+Enter submit.
 * Search           : the Desk search bar (Ctrl+K) is extended by the
 *                    `awesomebar_search` hook in diva_guard.
 */
(function () {
	"use strict";

	const DEFAULT_WAREHOUSE = "Stores - DD";
	const DEFAULT_PAYMENT_MODE = "Cash";
	const INVOICE_PRINT_FORMAT = "Diva Sales Invoice A4";
	const RECEIPT_PRINT_FORMAT = "Diva Purchase Receipt A4";
	const PCS_PER_DOZEN = 12;

	// ------------------------------------------------------------------
	// Helpers
	// ------------------------------------------------------------------
	function money(value) {
		return format_currency(flt(value), frappe.defaults.get_default("currency") || "EGP");
	}

	function is_new(frm) {
		return Boolean(frm && frm.doc && frm.doc.__islocal);
	}

	function is_draft(frm) {
		return Boolean(frm && frm.doc && frm.doc.docstatus === 0);
	}

	function is_submitted(frm) {
		return Boolean(frm && frm.doc && frm.doc.docstatus === 1);
	}

	function focus_field(frm, fieldname) {
		const field = frm && frm.fields_dict && frm.fields_dict[fieldname];
		if (!field) return;
		setTimeout(() => {
			if (typeof field.set_focus === "function") {
				field.set_focus();
			} else if (field.$input && field.$input.length) {
				field.$input.trigger("focus");
			}
			const input = field.$input && field.$input.get(0);
			if (input && input.select) input.select();
		}, 150);
	}

	function focus_item_row(frm) {
		const items = frm && frm.fields_dict && frm.fields_dict.items;
		const grid = items && items.grid;
		if (!grid) return;
		const rows = grid.grid_rows || [];
		if (!rows.length) {
			grid.add_new_row(null, null, true, null, true);
		} else {
			const last = rows[rows.length - 1];
			if (last && last.toggle_view) {
				last.toggle_view(true);
			}
		}
		setTimeout(() => {
			const current = grid.grid_rows || [];
			const row = current[current.length - 1];
			const itemCode = row && row.columns && row.columns.item_code;
			if (itemCode && typeof itemCode.set_focus === "function") {
				itemCode.set_focus();
			} else if (typeof grid.set_focus_on_row === "function") {
				grid.set_focus_on_row();
			}
		}, 300);
	}

	function open_print(doctype, name, printFormat) {
		const params = new URLSearchParams({
			doctype: doctype,
			name: name,
			format: printFormat,
			no_letterhead: "1",
		});
		window.open("/printview?" + params.toString(), "_blank");
	}

	function fieldname_of(element) {
		const control = $(element).closest("[data-fieldname]");
		return control.length ? control.attr("data-fieldname") : null;
	}

	// ------------------------------------------------------------------
	// EAN-13 label (drawn locally, no barcode service)
	// ------------------------------------------------------------------
	const EAN_L = [
		"0001101", "0011001", "0010011", "0111101", "0100011",
		"0110001", "0101111", "0111011", "0110111", "0001011",
	];
	const EAN_G = [
		"0100111", "0110011", "0011011", "0100001", "0011101",
		"0111001", "0000101", "0010001", "0001001", "0010111",
	];
	const EAN_R = [
		"1110010", "1100110", "1101100", "1000010", "1011100",
		"1001110", "1010000", "1000100", "1001000", "1110100",
	];
	const EAN_PARITY = [
		"LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
		"LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL",
	];

	function ean13Svg(code) {
		const value = String(code || "");
		if (!/^\d{13}$/.test(value)) return "";
		const digits = value.split("").map(Number);
		const parity = EAN_PARITY[digits[0]];
		let bits = "101";
		for (let i = 1; i <= 6; i++) {
			bits += parity[i - 1] === "L" ? EAN_L[digits[i]] : EAN_G[digits[i]];
		}
		bits += "01010";
		for (let i = 7; i <= 12; i++) bits += EAN_R[digits[i]];
		bits += "101";

		const module = 2;
		const height = 52;
		let x = 8;
		let bars = "";
		for (const bit of bits) {
			if (bit === "1") {
				bars += `<rect x="${x}" y="0" width="${module}" height="${height}" fill="#000"/>`;
			}
			x += module;
		}
		const width = x + 8;
		return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height + 16}" viewBox="0 0 ${width} ${height + 16}">
			<rect width="100%" height="100%" fill="#fff"/>
			${bars}
			<text x="${width / 2}" y="${height + 13}" font-family="monospace" font-size="10" text-anchor="middle">${value}</text>
		</svg>`;
	}

	function print_item_label(item) {
		const esc = frappe.utils.escape_html;
		const barcode = String(item.barcode || item.custom_barcode || "").trim();
		const svg = ean13Svg(barcode);
		const html = `<!doctype html><html><head><meta charset="utf-8"><style>
			@page { size: 50mm 30mm; margin: 2mm; }
			body { font-family: Arial, "Segoe UI", sans-serif; margin: 0; padding: 2mm; text-align: center; }
			.name { font-size: 11px; font-weight: 700; line-height: 1.15; }
			.code { font-size: 9px; margin-top: 2px; }
			.barcode { margin-top: 3px; }
			.barcode svg { max-width: 46mm; height: auto; }
			@media print { body { width: 46mm; } }
		</style></head><body>
			<div class="name">${esc(item.item_name || item.item_code || "")}</div>
			<div class="code">${esc(item.item_code || "")}</div>
			${svg ? `<div class="barcode">${svg}</div>` : `<div class="code">${esc(barcode)}</div>`}
		</body></html>`;
		const win = window.open("", "_blank", "width=420,height=320");
		if (!win) {
			frappe.msgprint(__("Please allow pop-ups to print the label."));
			return;
		}
		win.document.write(html);
		win.document.close();
		win.addEventListener("load", () => win.print());
	}

	// ------------------------------------------------------------------
	// Purchase Receipt: Add New Item dialog
	// ------------------------------------------------------------------
	function add_new_item_dialog(frm) {
		if (!frm || !is_draft(frm)) return;
		if (frm._diva_add_item_dialog) {
			frm._diva_add_item_dialog.show();
			return;
		}

		const warehouse = frm.doc.set_warehouse || DEFAULT_WAREHOUSE;
		const dialog = new frappe.ui.Dialog({
			title: __("Add New Item"),
			size: "large",
			fields: [
				{ fieldtype: "Section Break", label: __("Item") },
				{ fieldname: "item_code", label: __("Item Code"), fieldtype: "Data", reqd: 1 },
				{ fieldname: "item_name", label: __("Item Name"), fieldtype: "Data", reqd: 1 },
				{
					fieldname: "item_group",
					label: __("Item Group"),
					fieldtype: "Link",
					options: "Item Group",
					reqd: 1,
					default: "Accessories",
				},
				{
					fieldname: "barcode",
					label: __("Barcode (EAN-13)"),
					fieldtype: "Data",
					description: __("Leave it blank to generate an internal EAN-13 (starts with 20)."),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "buying_price",
					label: __("Buying Price (EGP/Dozen)"),
					fieldtype: "Currency",
					reqd: 1,
				},
				{
					fieldname: "selling_price",
					label: __("Selling Price (EGP/Dozen)"),
					fieldtype: "Currency",
					reqd: 1,
				},
				{
					fieldname: "selling_price_nos",
					label: __("Selling Price (EGP/Nos)"),
					fieldtype: "Currency",
					read_only: 1,
					description: __("One Dozen = 12 Nos; saved automatically."),
				},
				{ fieldtype: "Section Break", label: __("Receipt line") },
				{
					fieldname: "accepted_qty",
					label: __("Accepted Quantity (Dozen)"),
					fieldtype: "Float",
					default: 1,
					reqd: 1,
				},
				{ fieldname: "warehouse", label: __("Accepted Warehouse"), fieldtype: "Link", options: "Warehouse", reqd: 1, default: warehouse, read_only: 1 },
				{ fieldname: "print_label", label: __("Print the label after saving"), fieldtype: "Check", default: 1 },
			],
			primary_action_label: __("Save Item & Add"),
			primary_action(values) {
				dialog.hide();
				frappe.dom.freeze(__("Creating the item..."));
				frappe
					.xcall("diva_guard.desk_api.create_quick_item", {
						item_code: values.item_code,
						item_name: values.item_name,
						item_group: values.item_group,
						barcode: values.barcode || "",
						generate_barcode: 1,
						buying_price: values.buying_price,
						selling_price: values.selling_price,
						accepted_qty: values.accepted_qty,
						warehouse: values.warehouse || warehouse,
					})
					.then((item) => {
						frm.add_child("items", {
							item_code: item.item_code,
							item_name: item.item_name,
							qty: values.accepted_qty,
							uom: "Dozen",
							conversion_factor: PCS_PER_DOZEN,
							warehouse: item.warehouse || warehouse,
							rate: values.buying_price,
						});
						frm.refresh_field("items");
						if (values.print_label) print_item_label(item);
						frappe.show_alert({
							message: __("Item {0} added", [item.item_code]),
							indicator: "green",
						});
					})
					.catch((error) => {
						const message = (error && (error.message || error._server_messages)) || String(error);
						frappe.msgprint({
							title: __("Could not create the item"),
							message: message,
							indicator: "red",
						});
					})
					.finally(() => frappe.dom.unfreeze());
			},
		});

		dialog.fields_dict.selling_price.$input.on("change", () => {
			const dozens = flt(dialog.get_value("selling_price"));
			dialog.set_value("selling_price_nos", dozens > 0 ? dozens / PCS_PER_DOZEN : 0);
		});

		frm._diva_add_item_dialog = dialog;
		dialog.show();
	}

	frappe.ui.form.on("Purchase Receipt", {
		refresh(frm) {
			if (is_draft(frm)) {
				focus_field(frm, "supplier");
				frm.add_custom_button(__("Add New Item"), () => add_new_item_dialog(frm));
			}
			if (is_submitted(frm)) {
				frm.add_custom_button(__("Print"), () =>
					open_print("Purchase Receipt", frm.doc.name, RECEIPT_PRINT_FORMAT)
				);
			}
		},
	});

	// ------------------------------------------------------------------
	// Sales Invoice: Pay (full or partial) and Print
	// ------------------------------------------------------------------
	function pay_invoice_dialog(frm) {
		if (!is_submitted(frm) || flt(frm.doc.outstanding_amount) <= 0) {
			frappe.show_alert({
				message: __("This invoice has nothing left to pay."),
				indicator: "orange",
			});
			return;
		}
		const outstanding = flt(frm.doc.outstanding_amount);
		const dialog = new frappe.ui.Dialog({
			title: __("Pay Invoice {0}", [frm.doc.name]),
			fields: [
				{
					fieldname: "pay_full",
					label: __("Pay the full outstanding amount"),
					fieldtype: "Check",
					default: 1,
				},
				{
					fieldname: "amount",
					label: __("Amount to pay"),
					fieldtype: "Currency",
					reqd: 1,
					default: outstanding,
				},
				{
					fieldname: "mode_of_payment",
					label: __("Mode of Payment"),
					fieldtype: "Link",
					options: "Mode of Payment",
					reqd: 1,
					default: DEFAULT_PAYMENT_MODE,
				},
				{ fieldname: "reference_no", label: __("Reference No"), fieldtype: "Data" },
				{
					fieldname: "reference_date",
					label: __("Payment Date"),
					fieldtype: "Date",
					default: frappe.datetime.get_today(),
				},
				{
					fieldtype: "HTML",
					options: `<div class="text-muted small">${__(
						"Nothing is posted until you press Pay. The payment is then reviewed by a human, as always."
					)}</div>`,
				},
			],
			primary_action_label: __("Pay"),
			primary_action(values) {
				const amount = flt(values.amount);
				if (amount <= 0 || amount > outstanding + 0.005) {
					frappe.msgprint(
						__("Enter an amount between 0 and {0}", [money(outstanding)])
					);
					return;
				}
				dialog.hide();
				frappe.dom.freeze(__("Creating the payment..."));
				frappe
					.xcall("diva_guard.desk_api.pay_invoice", {
						invoice_name: frm.doc.name,
						amount: amount,
						mode_of_payment: values.mode_of_payment,
						reference_no: values.reference_no || "",
						reference_date: values.reference_date || frappe.datetime.get_today(),
					})
					.then((result) => {
						frappe.show_alert({
							message: __("Payment {0} submitted. Use Print for the invoice.", [
								result.payment_entry,
							]),
							indicator: "green",
						});
						frm.reload_doc();
					})
					.catch((error) => {
						frappe.msgprint({
							title: __("Payment failed"),
							message: (error && (error.message || error._server_messages)) || String(error),
							indicator: "red",
						});
					})
					.finally(() => frappe.dom.unfreeze());
			},
		});

		const syncAmountMode = () => {
			const full = Boolean(dialog.get_value("pay_full"));
			dialog.set_value("amount", full ? outstanding : flt(dialog.get_value("amount")) || outstanding);
			dialog.set_df_property("amount", "read_only", full ? 1 : 0);
			dialog.set_df_property(
				"amount",
				"description",
				full ? __("Full outstanding amount") : __("Partial payment")
			);
		};
		dialog.fields_dict.pay_full.$input.on("change", syncAmountMode);
		dialog.show();
		syncAmountMode();
		setTimeout(() => dialog.fields_dict.pay_full.$input.trigger("focus"), 150);
	}

	frappe.ui.form.on("Sales Invoice", {
		refresh(frm) {
			if (is_draft(frm)) {
				focus_field(frm, "customer");
			}
			if (is_submitted(frm)) {
				frm.add_custom_button(__("Print"), () =>
					open_print("Sales Invoice", frm.doc.name, INVOICE_PRINT_FORMAT)
				);
				if (flt(frm.doc.outstanding_amount) > 0) {
					frm.add_custom_button(__("Pay"), () => pay_invoice_dialog(frm));
				}
			}
		},
	});

	// ------------------------------------------------------------------
	// Keyboard shortcuts
	// ------------------------------------------------------------------
	function shortcut_help() {
		const rows = [
			["F1", __("Show these shortcuts")],
			["F2", __("Focus customer / supplier")],
			["F3", __("Add or focus the item row")],
			["F8", __("Pay the Sales Invoice")],
			["F9", __("Print the current document")],
			["Tab", __("Accept the first suggestion, then jump on")],
			["Ctrl+S", __("Save")],
			["Ctrl+Enter", __("Submit")],
			["Ctrl+K", __("Search items, parties and invoices")],
		];
		const html = `<table class="table table-sm">${rows
			.map(
				([key, label]) =>
					`<tr><td style="width:110px"><kbd>${key}</kbd></td><td>${label}</td></tr>`
			)
			.join("")}</table>`;
		frappe.msgprint({ title: __("Diva shortcuts"), message: html, wide: true });
	}

	// Tab accepts the first open Link suggestion instead of leaving the field.
	function select_first_link_suggestion(input) {
		if (!input.value || !input.value.trim()) return false;
		const list = input.closest ? input.closest(".awesomplete") : null;
		const ul = list && list.querySelector("ul[role='listbox']");
		if (!ul || ul.hasAttribute("hidden") || !ul.children.length) return false;
		const fire = (key, keyCode) =>
			input.dispatchEvent(
				new KeyboardEvent("keydown", {
					key: key,
					keyCode: keyCode,
					which: keyCode,
					bubbles: true,
					cancelable: true,
				})
			);
		fire("ArrowDown", 40);
		fire("Enter", 13);
		return true;
	}

	function tab_target(frm, fieldname) {
		if (!frm) return null;
		if (frm.doctype === "Purchase Receipt") {
			if (fieldname === "supplier") return () => focus_field(frm, "set_warehouse");
			if (fieldname === "set_warehouse") return () => focus_item_row(frm);
		}
		if (frm.doctype === "Sales Invoice" && fieldname === "customer") {
			return () => focus_item_row(frm);
		}
		return null;
	}

	function active_form() {
		return window.cur_frm && window.cur_frm.doc ? window.cur_frm : null;
	}

	function dialog_is_open() {
		return $(".modal:visible").length > 0;
	}

	document.addEventListener(
		"keydown",
		(event) => {
			const input = event.target;
			if (event.key === "Tab" && input && input.tagName === "INPUT") {
				const frm = active_form();
				const fieldname = fieldname_of(input);
				const jump = frm && !dialog_is_open() ? tab_target(frm, fieldname) : null;
				// Supplier -> warehouse -> items and Customer -> items always jump.
				// Any other Link field accepts the first suggestion when it has text.
				if (jump) {
					event.preventDefault();
					jump();
					return;
				}
				if (select_first_link_suggestion(input)) {
					event.preventDefault();
				}
			}

			if (event.key === "F1") {
				event.preventDefault();
				shortcut_help();
				return;
			}

			const frm = active_form();
			if (!frm || dialog_is_open()) return;
			const isSalesInvoice = frm.doctype === "Sales Invoice";
			const isPurchaseReceipt = frm.doctype === "Purchase Receipt";

			if (event.key === "F2") {
				event.preventDefault();
				if (isPurchaseReceipt) focus_field(frm, "supplier");
				else if (isSalesInvoice) focus_field(frm, "customer");
			} else if (event.key === "F3") {
				event.preventDefault();
				focus_item_row(frm);
			} else if (event.key === "F8" && isSalesInvoice) {
				event.preventDefault();
				pay_invoice_dialog(frm);
			} else if (event.key === "F9" && is_submitted(frm)) {
				event.preventDefault();
				if (isSalesInvoice) open_print("Sales Invoice", frm.doc.name, INVOICE_PRINT_FORMAT);
				else if (isPurchaseReceipt) {
					open_print("Purchase Receipt", frm.doc.name, RECEIPT_PRINT_FORMAT);
				}
			} else if (event.key.toLowerCase() === "s" && (event.ctrlKey || event.metaKey)) {
				event.preventDefault();
				frm.save();
			} else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
				event.preventDefault();
				if (frm.doc.docstatus === 0) frm.save("Submit");
			}
		},
		true
	);
})();
