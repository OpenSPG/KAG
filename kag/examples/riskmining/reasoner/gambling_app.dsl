MATCH
    (u:`RiskMining.TaxOfRiskUser`/`赌博App开发者`)-[:developed]->(app:`RiskMining.TaxOfRiskApp`/`赌博应用`),
    (b:`RiskMining.TaxOfRiskUser`/`赌博App老板`)-[:release]->(app)
RETURN u.name, b.name ,app.id
