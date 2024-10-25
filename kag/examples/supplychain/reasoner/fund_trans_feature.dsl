MATCH (s:SupplyChain.Company)
RETURN s.id, s.fundTrans1Month, s.fundTrans3Month, s.fundTrans6Month, s.fundTrans1MonthIn, s.fundTrans3MonthIn, s.fundTrans6MonthIn
