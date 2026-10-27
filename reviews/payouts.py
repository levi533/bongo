COUNTRIES = [
    ("DZ", "Algérie", "AF"), ("AO", "Angola", "AF"), ("BJ", "Bénin", "AF"),
    ("BW", "Botswana", "AF"), ("BF", "Burkina Faso", "AF"), ("BI", "Burundi", "AF"),
    ("CV", "Cap-Vert", "AF"), ("CM", "Cameroun", "AF"),
    ("CF", "République centrafricaine", "AF"), ("TD", "Tchad", "AF"),
    ("KM", "Comores", "AF"), ("CG", "République du Congo", "AF"),
    ("CD", "République démocratique du Congo", "AF"),
    ("CI", "Côte d’Ivoire", "AF"), ("DJ", "Djibouti", "AF"), ("EG", "Égypte", "AF"),
    ("GQ", "Guinée équatoriale", "AF"), ("ER", "Érythrée", "AF"),
    ("SZ", "Eswatini", "AF"), ("ET", "Éthiopie", "AF"), ("GA", "Gabon", "AF"),
    ("GM", "Gambie", "AF"), ("GH", "Ghana", "AF"), ("GN", "Guinée", "AF"),
    ("GW", "Guinée-Bissau", "AF"), ("KE", "Kenya", "AF"), ("LS", "Lesotho", "AF"),
    ("LR", "Libéria", "AF"), ("LY", "Libye", "AF"), ("MG", "Madagascar", "AF"),
    ("MW", "Malawi", "AF"), ("ML", "Mali", "AF"), ("MR", "Mauritanie", "AF"),
    ("MU", "Maurice", "AF"), ("MA", "Maroc", "AF"), ("MZ", "Mozambique", "AF"),
    ("NA", "Namibie", "AF"), ("NE", "Niger", "AF"), ("NG", "Nigéria", "AF"),
    ("RW", "Rwanda", "AF"), ("ST", "Sao Tomé-et-Principe", "AF"),
    ("SN", "Sénégal", "AF"), ("SC", "Seychelles", "AF"),
    ("SL", "Sierra Leone", "AF"), ("SO", "Somalie", "AF"),
    ("ZA", "Afrique du Sud", "AF"), ("SS", "Soudan du Sud", "AF"),
    ("SD", "Soudan", "AF"), ("TZ", "Tanzanie", "AF"), ("TG", "Togo", "AF"),
    ("TN", "Tunisie", "AF"), ("UG", "Ouganda", "AF"), ("ZM", "Zambie", "AF"),
    ("ZW", "Zimbabwe", "AF"),
    ("AL", "Albanie", "EU"), ("AD", "Andorre", "EU"), ("AM", "Arménie", "EU"),
    ("AT", "Autriche", "EU"), ("AZ", "Azerbaïdjan", "EU"),
    ("BY", "Biélorussie", "EU"), ("BE", "Belgique", "EU"),
    ("BA", "Bosnie-Herzégovine", "EU"), ("BG", "Bulgarie", "EU"),
    ("HR", "Croatie", "EU"), ("CY", "Chypre", "EU"), ("CZ", "Tchéquie", "EU"),
    ("DK", "Danemark", "EU"), ("EE", "Estonie", "EU"), ("FI", "Finlande", "EU"),
    ("FR", "France", "EU"), ("GE", "Géorgie", "EU"), ("DE", "Allemagne", "EU"),
    ("GR", "Grèce", "EU"), ("HU", "Hongrie", "EU"), ("IS", "Islande", "EU"),
    ("IE", "Irlande", "EU"), ("IT", "Italie", "EU"), ("KZ", "Kazakhstan", "EU"),
    ("XK", "Kosovo", "EU"), ("LV", "Lettonie", "EU"), ("LI", "Liechtenstein", "EU"),
    ("LT", "Lituanie", "EU"), ("LU", "Luxembourg", "EU"), ("MT", "Malte", "EU"),
    ("MD", "Moldavie", "EU"), ("MC", "Monaco", "EU"), ("ME", "Monténégro", "EU"),
    ("NL", "Pays-Bas", "EU"), ("MK", "Macédoine du Nord", "EU"),
    ("NO", "Norvège", "EU"), ("PL", "Pologne", "EU"), ("PT", "Portugal", "EU"),
    ("RO", "Roumanie", "EU"), ("RU", "Russie", "EU"), ("SM", "Saint-Marin", "EU"),
    ("RS", "Serbie", "EU"), ("SK", "Slovaquie", "EU"), ("SI", "Slovénie", "EU"),
    ("ES", "Espagne", "EU"), ("SE", "Suède", "EU"), ("CH", "Suisse", "EU"),
    ("TR", "Turquie", "EU"), ("UA", "Ukraine", "EU"),
    ("GB", "Royaume-Uni", "EU"), ("VA", "Vatican", "EU"),
    ("US", "États-Unis", "OTHER"),
]

_BANK_PAYOUTS = {
    "CM": "XAF",
    "CI": "XOF",
    "EG": "EGP",
    "GH": "GHS",
    "KE": "KES",
    "MW": "MWK",
    "NG": "NGN",
    "RW": "RWF",
    "SN": "XOF",
    "ZA": "ZAR",
    "TZ": "TZS",
    "UG": "UGX",
    "GB": "GBP",
}

_MOBILE_PAYOUTS = {
    "CI": "XOF",
    "EG": "EGP",
    "GH": "GHS",
    "KE": "KES",
    "RW": "RWF",
    "SN": "XOF",
    "UG": "UGX",
}

_SEPA_COUNTRIES = {
    "AD", "AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES",
    "FI", "FR", "GR", "HR", "HU", "IE", "IS", "IT", "LI", "LT",
    "LU", "LV", "MC", "MT", "NL", "NO", "PL", "PT", "RO", "SE", "SI",
    "SK", "SM", "VA",
}


def payout_options():
    options = []
    for code, name, region in COUNTRIES:
        bank_currency = _BANK_PAYOUTS.get(code)
        if code in _SEPA_COUNTRIES:
            bank_currency = "EUR"
        channels = {}
        if bank_currency:
            channels["bank"] = bank_currency
        if code in _MOBILE_PAYOUTS:
            channels["mobile"] = _MOBILE_PAYOUTS[code]
        options.append(
            {
                "code": code,
                "name": name,
                "region": region,
                "channels": channels,
            }
        )
    return options


def destination_currency(country_code, payout_method):
    option = next(
        (country for country in payout_options() if country["code"] == country_code),
        None,
    )
    if not option or payout_method not in option["channels"]:
        return None
    return option["channels"][payout_method]
