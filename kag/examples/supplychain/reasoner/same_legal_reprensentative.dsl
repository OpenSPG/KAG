MATCH (s:SupplyChain.Company)-[p:sameLegalRepresentative]->(o:SupplyChain.Company)
RETURN s.id, o.id
