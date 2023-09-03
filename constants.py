LEAGUE_IDs = [
    ( "Premier League" , "premier-league", "65" ),
    ( "La Liga", "laliga", "75" ),
    ( "Seria A", "serie-a", "77" ),
    ( "Bundesliga", "bundesliga", "67" ),
    ( "Ligue 1", "ligue-1", "68" ),
    ( "Champions League", "uefa-champions-league", "60" ),
    ( "Europa League", "uefa-europa-league", "36" )
]

CURRENCY_LIST = [
    ("Nigeria", "NG", "Naira" ,"NGN"),
    ("Ghana", "GH", "Cedi", "GHS"),
    ("Tanzania", "TZ", "Shiling", "TZS"),
    ("Kenya", "KE", "Shiling", "KES"),
    ("Uganda", "UG", "Shiling", "UGX"),
]

NAIJA_BANKS = [
    {
      "id": 14,
      "code": "032",
      "name": "Union Bank PLC"
    },
    {
      "id": 13,
      "code": "033",
      "name": "United Bank for Africa"
    },
    {
      "id": 15,
      "code": "035",
      "name": "Wema Bank PLC"
    },
    {
      "id": 1,
      "code": "044",
      "name": "Access Bank"
    },
    {
      "id": 4,
      "code": "050",
      "name": "EcoBank PLC"
    },
    {
      "id": 5,
      "code": "011",
      "name": "First Bank PLC"
    },
    {
      "id": 10,
      "code": "221",
      "name": "Stanbic IBTC Bank"
    },
    {
      "id": 12,
      "code": "232",
      "name": "Sterling Bank PLC"
    },
    {
      "id": 784,
      "code": "305",
      "name": "Paycom"
    },
    {
      "id": 254,
      "code": "090267",
      "name": "Kuda"
    },
    {
      "id": 16,
      "code": "057",
      "name": "Zenith bank PLC"
    },
    {
      "id": 8,
      "code": "058",
      "name": "Guaranty Trust Bank"
    },
    {
      "id": 11,
      "code": "068",
      "name": "Standard Chaterted bank PLC"
    },
    {
      "id": 1864,
      "code": "090405",
      "name": "Moniepoint Microfinance Bank"
    },
    {
      "id": 1861,
      "code": "090409",
      "name": "Fcmb Microfinance Bank"
    },
    {
      "id": 7,
      "code": "070",
      "name": "Fidelity Bank"
    },
    {
      "id": 1435,
      "code": "100004",
      "name": "Opay"
    },
    {
      "id": 990,
      "code": "100033",
      "name": "PALMPAY"
    },
    {
      "id": 9,
      "code": "076",
      "name": "Polaris bank"
    },
    {
      "id": 183,
      "code": "082",
      "name": "Keystone Bank"
    },
    {
      "id": 660,
      "code": "090110",
      "name": "VFD Micro Finance Bank"
    },
    {
      "id": 876,
      "code": "090139",
      "name": "Visa Microfinance Bank"
    },
    {
      "id": 639,
      "code": "090328",
      "name": "Eyowo MFB"
    },
    {
      "id": 1801,
      "code": "090479",
      "name": "First Heritage Microfinance Bank"
    },
    {
      "id": 1733,
      "code": "090551",
      "name": "Fairmoney Microfinance Bank Ltd"
    },
    {
      "id": 953,
      "code": "100011",
      "name": "Mkudi"
    },
    {
      "id": 18,
      "code": "101",
      "name": "ProvidusBank PLC"
    }
]

P2P_BET_LIST = [
    {
        "id" : 0,
        "name" : "1X2",
        "description" : "A Peer (booker) predicts that the Home to win the match or Away to win the match or the match ends in a Draw while another peer (marquee) wagers against the outcome.",
        "options" : [
            {
                "name" : "1",
                "description" : "Home Team to win the match.",
                "options" : [ "X", "2" ]
            },
            {
                "name" : "X",
                "description" : "The match ends in a Draw.",
                "options" : [ "1", "2" ]
            },
            {
                "name" : "2",
                "description" : "Away Team to win the match.",
                "options" : [ "1", "X" ]
            }
        ]
    },
    {
        "id" : 1,
        "name" : "GG/NG",
        "description" : "A Peer (booker) predicts that either both teams score or any of the teams not to score in the match while another peer (marquee) wagers against the outcome.",
        "options" : [
            {
                "name" : "GG",
                "description" : "Both teams score in the match.",
                "options" : [ "NG" ]
            },
            {
                "name" : "NG",
                "description" : "Any of the teams not to score in the match.",
                "options" : [ "GG" ]
            }
        ]
    },
    {
        "id" : 2,
        "name" : "Over/Under",
        "description" : "A Peer (booker) predicts that over/under a certain amount of goals is scored in the match while another peer(marquee) wagers against the outcome",
        "options" : [
            {
                "name" : "Over 0.5",
                "description" : "Over 1(one) or more goals is scored in the match.",
                "options" : [ "Under 0.5" ]
            },
            {
                "name" : "Under 0.5",
                "description" : "Under 1(one) or Zero goals is scored in the match.",
                "options" : [ "Over 0.5" ]
            },
            {
                "name" : "Over 1.5",
                "description" : "Over 2(two) or more goals is scored in the match.",
                "options" : [ "Under 1.5" ]
            },
            {
                "name" : "Under 1.5",
                "description" : "Under 2(two) goals is scored in the match.",
                "options" : [ "Over 1.5" ]
            },
            {
                "name" : "Over 2.5",
                "description" : "Over 3(three) or more goals is scored in the match.",
                "options" : [ "Under 2.5" ]
            },
            {
                "name" : "Under 2.5",
                "description" : "Under 3(three) goals is scored in the match.",
                "options" : [ "Over 2.5" ]
            },
            {
                "name" : "Over 3.5",
                "description" : "Over 4(four) or more goals is scored in the match.",
                "options" : [ "Under 3.5" ]
            },
            {
                "name" : "Under 3.5",
                "description" : "Under 4(four) goals is scored in the match.",
                "options" : [ "Over 3.5" ]
            },
            {
                "name" : "Over 4.5",
                "description" : "Over 5(five) or more goals is scored in the match.",
                "options" : [ "Under 4.5" ]
            },
            {
                "name" : "Under 4.5",
                "description" : "Under 5(five) goals is scored in the match.",
                "options" : [ "Over 4.5" ]
            },
            {
                "name" : "Over 5.5",
                "description" : "Over 6(six) or more goals is scored in the match.",
                "options" : [ "Under 5.5" ]
            },
            {
                "name" : "Under 5.5",
                "description" : "Under 6(six) goals is scored in the match.",
                "options" : [ "Over 5.5" ]
            },
            {
                "name" : "Over 6.5",
                "description" : "Over 7(seven) or more goals is scored in the match.",
                "options" : [ "Under 6.5" ]
            },
            {
                "name" : "Under 6.5",
                "description" : "Under 7(seven) goals is scored in the match.",
                "options" : [ "Over 6.5" ]
            }
        ]
    },
    {
        "id" : 3,
        "name" : "Player to Score",
        "description" : "A Peer (booker) predicts that a player would score while another peer (marquee) wagers against the outcome.",
        "options" : [ "Player Not to Score" ]
    },
    {
        "id" : 4,
        "name" : "Correct Score",
        "description" : "A Peer (booker) predicts the exact score of a match while another peer (marquee) wagers against the outcome..",
        "options" : [ "Not the Correct Score" ]
    },
    {
        "id" : 5,
        "name" : "Exact Goals",
        "description" : "A Peer (booker) predicts the exact goals of a match while another peer (marquee) wagers against the outcome..",
        "options" : [ "Not the Exact Goals" ]
    },
    {
        "id" : 6,
        "name" : "1st Goal",
        "description" : "A Peer (booker) predicts the team to score the 1st goal of a match while another peer (marquee) wagers against the outcome..",
        "options" : [
            {
                "name" : "1",
                "description" : "Home team to score the 1st goal in the match.",
                "options" : [ "2" ]
            },
            {
                "name" : "2",
                "description" : "Away team to score the 1st goal in the match.",
                "options" : [ "1" ]
            }
        ]
    },
    {
        "id" : 7,
        "name" : "Odd/Even",
        "description" : "A Peer (booker) predicts the number of goals scored in a match to be an Odd number or Even number while another peer (marquee) wagers against the outcome..",
        "options" : [
            {
                "name" : "Odd",
                "description" : "Odd number of goals scored in the match.",
                "options" : [ "Even" ]
            },
            {
                "name" : "Even",
                "description" : "Even number of goals scored in the match.",
                "options" : [ "Odd" ]
            }
        ]
    }
]