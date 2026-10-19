from verifier import check_claim, extract_claims

src = "Modern recycling facilities can recover between 85 and 95 percent of a panel's total mass, depending on the panel type."

print(check_claim("Facilities recover 85-95% of a panel's mass.", src))
print(check_claim("Recycling a panel costs $15 to $45.", src))
print(extract_claims("Intro line. Recovery is high [1]. Costs vary [2, 3]. No cite here."))
