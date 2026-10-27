const menuButton = document.querySelector(".menu-toggle");
const menu = document.querySelector("#primary-menu");

if (menuButton && menu) {
    menuButton.addEventListener("click", () => {
        const isOpen = menuButton.getAttribute("aria-expanded") === "true";
        menuButton.setAttribute("aria-expanded", String(!isOpen));
        menu.classList.toggle("is-open", !isOpen);
    });

    menu.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
            menuButton.setAttribute("aria-expanded", "false");
            menu.classList.remove("is-open");
        });
    });
}

const commentField = document.querySelector("#id_comment");
const commentCount = document.querySelector("#comment-count");

if (commentField && commentCount) {
    const updateCount = () => {
        commentCount.textContent = `${commentField.value.length} / 1000`;
    };

    const formatAmount = (value) => new Intl.NumberFormat("fr-FR", {
        maximumFractionDigits: 2,
    }).format(Number(value));

    async function requestQuote(amount, source, destination) {
        const query = new URLSearchParams({
            amount,
            from: source,
            to: destination,
        });
        const response = await fetch(`/api/transfers/quote/?${query}`, {
            headers: { Accept: "application/json" },
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Le taux n’a pas pu être récupéré.");
        }
        return data;
    }

    const converterAmount = document.querySelector("#converter-amount");
    const converterFrom = document.querySelector("#converter-from");
    const converterTo = document.querySelector("#converter-to");
    const converterResult = document.querySelector("#converter-result");
    const converterStatus = document.querySelector("#converter-status");

    if (converterAmount && converterFrom && converterTo && converterResult && converterStatus) {
        let quoteTimer;
        const refreshConverter = () => {
            window.clearTimeout(quoteTimer);
            quoteTimer = window.setTimeout(async () => {
                converterStatus.textContent = "Récupération du taux Flutterwave…";
                try {
                    const quote = await requestQuote(
                        converterAmount.value,
                        converterFrom.value,
                        converterTo.value,
                    );
                    converterResult.value = formatAmount(quote.destination_amount);
                    converterStatus.textContent =
                        `1 ${quote.source_currency} = ${formatAmount(quote.rate)} ${quote.destination_currency}`;
                } catch (error) {
                    converterResult.value = "—";
                    converterStatus.textContent = error.message;
                }
            }, 300);
        };

        [converterAmount, converterFrom, converterTo].forEach((field) => {
            field.addEventListener("input", refreshConverter);
            field.addEventListener("change", refreshConverter);
        });
        refreshConverter();
    }

    const transferForm = document.querySelector("#transfer-form");

    if (transferForm) {
        const countryField = transferForm.querySelector("#transfer-country");
        const methodField = transferForm.querySelector("#payout-method");
        const recipientFields = transferForm.querySelector("#recipient-fields");
        const destinationHint = transferForm.querySelector("#destination-hint");
        const accountLabel = transferForm.querySelector("#account-number-label");
        const bankCodeLabel = transferForm.querySelector("#bank-code-label");
        const bankExtras = transferForm.querySelector("#bank-extra-fields");
        const bankCode = transferForm.querySelector("#bank-code");
        const networkCode = transferForm.querySelector("#network-code");
        const accountType = transferForm.querySelector("#account-type");
        const accountTypeField = accountType.closest(".field");
        const gbpRecipientFields = transferForm.querySelector("#gbp-recipient-fields");
        const businessRecipientField = transferForm.querySelector("#business-recipient-field");
        const transferAmount = transferForm.querySelector("#transfer-amount");
        const transferCurrency = transferForm.querySelector("#transfer-currency");
        const formStatus = transferForm.querySelector("#transfer-form-status");
        const submitButton = transferForm.querySelector('button[type="submit"]');

        const setGroupEnabled = (group, enabled) => {
            group.querySelectorAll("input, select").forEach((field) => {
                field.disabled = !enabled;
            });
        };

        setGroupEnabled(recipientFields, false);

        const getSelectedCurrency = () => {
            const selected = countryField.selectedOptions[0];
            if (!selected || !selected.value || !methodField.value) {
                return "";
            }
            return selected.dataset[`${methodField.value}Currency`] || "";
        };

        const updateAccountTypeOptions = () => {
            const currency = getSelectedCurrency();
            const options = currency === "USD"
                ? [["checking", "Checking"], ["depository", "Depository"]]
                : currency === "GBP"
                    ? [["personal", "Personnel"], ["corporate", "Professionnel"]]
                    : [];
            accountType.replaceChildren(new Option("Choisir", ""));
            options.forEach(([value, label]) => {
                accountType.add(new Option(label, value));
            });
            accountType.disabled = options.length === 0;
            accountTypeField.classList.toggle("hidden", options.length === 0);
        };

        const updateGbpRecipientFields = () => {
            const isGbp = getSelectedCurrency() === "GBP";
            const isCorporate = accountType.value === "corporate";
            gbpRecipientFields.classList.toggle("hidden", !isGbp || isCorporate);
            businessRecipientField.classList.toggle("hidden", !isGbp || !isCorporate);
            gbpRecipientFields.querySelectorAll("input").forEach((field) => {
                field.disabled = !isGbp || isCorporate;
            });
            businessRecipientField.querySelector("input").disabled = !isGbp || !isCorporate;
        };

        const refreshTransferQuote = async () => {
            const destination = getSelectedCurrency();
            if (!destination || !transferAmount.value) {
                destinationHint.textContent = "";
                return;
            }
            destinationHint.textContent = "Estimation du montant reçu…";
            try {
                const quote = await requestQuote(
                    transferAmount.value,
                    transferCurrency.value,
                    destination,
                );
                destinationHint.textContent =
                    `Montant estimé reçu : ${formatAmount(quote.destination_amount)} ${destination} (hors frais).`;
            } catch (error) {
                destinationHint.textContent = error.message;
            }
        };

        countryField.addEventListener("change", () => {
            const selected = countryField.selectedOptions[0];
            const channels = selected?.dataset.channels?.split(",").filter(Boolean) || [];
            methodField.replaceChildren(new Option("Choisir un mode", ""));
            channels.forEach((channel) => {
                const label = channel === "mobile" ? "Mobile Money" : "Virement bancaire";
                methodField.add(new Option(label, channel));
            });
            methodField.disabled = channels.length === 0;
            recipientFields.classList.add("hidden");
            setGroupEnabled(recipientFields, false);
            destinationHint.textContent = channels.length
                ? "Les coordonnées seront demandées pour le mode choisi."
                : "Les versements ne sont pas proposés pour ce pays via ce parcours.";
        });

        methodField.addEventListener("change", () => {
            if (!methodField.value) {
                recipientFields.classList.add("hidden");
                setGroupEnabled(recipientFields, false);
                return;
            }
            recipientFields.classList.remove("hidden");
            setGroupEnabled(recipientFields, true);
            const isBank = methodField.value === "bank";
            bankExtras.classList.toggle("hidden", !isBank);
            setGroupEnabled(bankExtras, isBank);
            bankCode.hidden = !isBank;
            bankCode.disabled = !isBank;
            networkCode.hidden = isBank;
            networkCode.disabled = isBank;
            networkCode.required = !isBank;
            if (!isBank) {
                networkCode.replaceChildren(new Option("Choisir un réseau", ""));
                const networks = {
                    CI: { FMM: "FMM", Moov: "Moov", orangemoney: "Orange Money", WAVE: "Wave" },
                    EG: { EGPWALLETS: "Portefeuilles mobiles" },
                    GH: { AIRTELTIGO: "AirtelTigo", MTN: "MTN", TELECEL: "Telecel", VODAFONE: "Vodafone" },
                    KE: { SAFARICOM: "Safaricom", "T-Kash": "T-Kash", Airtel: "Airtel", MPS: "M-Pesa" },
                    RW: { MPS: "M-Pesa", MTN: "MTN" },
                    SN: { freemoney: "Free Money", orangemoney: "Orange Money", WAVE: "Wave" },
                    UG: { Airtel: "Airtel", MPS: "M-Pesa", MTN: "MTN" },
                };
                const options = networks[countryField.value] || {};
                Object.entries(options).forEach(([value, label]) => {
                    networkCode.add(new Option(label, value));
                });
            } else {
                bankCode.required = true;
            }
            updateAccountTypeOptions();
            updateGbpRecipientFields();
            accountLabel.textContent = isBank ? "IBAN ou numéro de compte" : "Numéro Mobile Money";
            bankCodeLabel.textContent = isBank ? "Code banque / réseau" : "Réseau Mobile Money";
            refreshTransferQuote();
        });

        accountType.addEventListener("change", () => {
            updateGbpRecipientFields();
        });

        [transferAmount, transferCurrency].forEach((field) => {
            field.addEventListener("input", refreshTransferQuote);
            field.addEventListener("change", refreshTransferQuote);
        });

        transferForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            formStatus.textContent = "";
            submitButton.disabled = true;
            submitButton.setAttribute("aria-busy", "true");
            try {
                const response = await fetch(transferForm.action, {
                    method: "POST",
                    body: new FormData(transferForm),
                    headers: { Accept: "application/json" },
                });
                const data = await response.json();
                if (!response.ok) {
                    const firstFieldError = Object.values(data.errors || {})
                        .flat()
                        .find(Boolean);
                    throw new Error(firstFieldError || data.error || "Impossible de démarrer le transfert.");
                }
                if (!data.checkout_url) {
                    throw new Error("Flutterwave n’a pas fourni de lien de paiement.");
                }
                window.location.assign(data.checkout_url);
            } catch (error) {
                formStatus.textContent = error.message;
                submitButton.disabled = false;
                submitButton.removeAttribute("aria-busy");
            }
        });
    }

    commentField.addEventListener("input", updateCount);
    updateCount();
}
