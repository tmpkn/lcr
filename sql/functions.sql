CREATE FUNCTION lcr_dialplan(ip_switch text DEFAULT '0.0.0.0'::text, ip_customer text DEFAULT '0.0.0.0'::text, dn text DEFAULT '000'::text) RETURNS TABLE(deal_id integer, ip_switch text, ip_customer text, price_cust numeric, dest_name text, prefix text, price_supp numeric, ip_destination text, tech_prefix text, cust_prefix text)
    LANGUAGE sql
    AS $_$SELECT deal.id AS deal_id, switch.ip_addr AS ip_switch, cip.ip_addr AS ip_customer, deal.buy_price AS price_cust, dest.name AS dest_name, 
code AS prefix, deal.sell_price AS price_supp, dest.ip_addr AS ip_destination, dest.tech_prefix AS tech_prefix, cust.tech_prefix AS cust_prefix
FROM 
matrix_lcrdestinatione164 e164, matrix_lcrdestination dest, matrix_lcrdeal deal, matrix_lcrcustomer cust,
matrix_lcrcustomerip cip, matrix_lcrswitch AS switch
WHERE 1=1
AND e164.destination_id = dest.id
AND deal.destination_id = dest.id
AND deal.buy_carrier_id = cust.id
AND cip.customer_id = cust.id
AND cust.switch_id = switch.id
AND deal.is_active = 1
AND switch.ip_addr = $1
AND cip.ip_addr = $2
AND code::prefix_range @> replace($3, cust.tech_prefix, '')
ORDER BY prefix DESC$_$;

CREATE FUNCTION rcdr_rate() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
                IF NEW.billsec IS NOT NULL THEN
                        NEW.value_cust = NEW.price_cust * NEW.billsec / 60;
                        NEW.value_supp = NEW.price_supp * NEW.billsec / 60;
                END IF;
                RETURN NEW;
        END;
$$;

