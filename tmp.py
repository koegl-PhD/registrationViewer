positive = ["guqcK-4iXaE",
            "zNsYMilmwCo",
            "yYcNJD5knnY",
            "YPEbc0OFC8I",
            "yIt7Z7VHXU0",
            "y9Zc0VfK-hE",
            "xYbaegYf_mw",
            "XKgRKTaLeEo",
            "WeMcC01ZNgY",
            "VUIaoA1iqhI",
            "urqkluKweXA",
            "ur1u5glVZIE",
            "TwU508CCA9Y",
            "TMxGak0IQOg",
            "pP5CHNLQspI",
            "pnxsbLeerXU",
            "LeJQ4K8qv5c",
            "LB9oATPd0mE",
            "iqzgKhiRxxc",
            "hmJfXqxVMk0",
            "fNvYEk8SSJs"]

negative = ["ZmTnkjJY0WA",
            "7SwVHAAw5lM",
            "wl0SZz-0IAI",
            "hkvdD_XVYqo",
            "CSSdmYlgjew",
            "7IZ0hAktN78",
            "PfzTYxllBQc",
            "g-chOlbtzBQ",
            "96-du2ceM4o",
            "87J-_CHHkzI",
            "UoYxcCNwdxA",
            "J0XX6t7vZ1I",
            "vQC_zG5VpaI",
            "ccucLKGWtSQ",
            "XliJZuWCOzs",
            "VIhRI27e_qA",
            "tpcakZfjy40",
            "tjrrBb3AK9M",
            "SAxkPtG7yrk",
            "pEQnvh_Lbhc",
            "og9nL1ncPf4"]

transformations = ["none", "rigid", "deformable"]

positive_none = [(pos, "none", "positive") for pos in positive]
positive_rigid = [(pos, "rigid", "positive") for pos in positive]
positive_deformable = [(pos, "deformable", "positive") for pos in positive]

neagtive_none = [(neg, "none", "negative") for neg in negative]
negative_rigid = [(neg, "rigid", "negative") for neg in negative]
negative_deformable = [(neg, "deformable", "negative") for neg in negative]


g1 = positive_none[0:7] + neagtive_none[0:7] + \
    positive_rigid[7:14] + negative_rigid[7:14] + \
    positive_deformable[14:21] + negative_deformable[14:21]

g2 = positive_rigid[0:7] + negative_rigid[0:7] + \
    positive_deformable[7:14] + negative_deformable[7:14] + \
    positive_none[14:21] + neagtive_none[14:21]

g3 = positive_deformable[0:7] + negative_deformable[0:7] + \
    positive_none[7:14] + neagtive_none[7:14] + \
    positive_rigid[14:21] + negative_rigid[14:21]


# print group titles above
print(f"{2 * '\t'}{'Group 1'}{7 * '\t'}{'Group 2'}{7 * '\t'}{'Group 3'}")

for p1, p2, p3 in zip(g1, g2, g3):
    if p1[1] != "deformable":
        t1 = 2
    else:
        t1 = 1

    if p2[1] != "deformable":
        t2 = 2
    else:
        t2 = 1
    if p3[1] != "deformable":
        t3 = 2
    else:
        t3 = 1

    print(
        f"{p1[0]}\t{p1[1]}{t1*'\t'}{p1[2]}\t\t{p2[0]}\t{p2[1]}{t2*'\t'}{p2[2]}\t\t{p3[0]}\t{p3[1]}{t3*'\t'}{p3[2]}"
    )

x = 0
