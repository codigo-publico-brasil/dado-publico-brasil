-- Fusões de pessoas (ADR 0013): quando duas chaves se mostram a mesma pessoa (por exemplo, deputado que virou
-- senador), a mais nova é absorvida pela mais antiga. A chave absorvida nunca é reaproveitada, e quem a guardou
-- resolve a atual por esta tabela.
CREATE TABLE IF NOT EXISTS identity.pessoa_fusao (
    id_pessoa_absorvida BIGINT PRIMARY KEY,
    id_pessoa_sobrevivente BIGINT NOT NULL,
    metodo VARCHAR NOT NULL,
    fundida_em VARCHAR NOT NULL
);
