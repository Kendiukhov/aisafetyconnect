-- Schema para OpenAlex Extractor basado en schema.dbml
-- Crear tablas de taxonomía y papers

-- Tabla area
CREATE TABLE IF NOT EXISTS area (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla field
CREATE TABLE IF NOT EXISTS field (
    id SERIAL PRIMARY KEY,
    area_id TEXT NOT NULL REFERENCES area(id),
    name TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(area_id, name)
);

-- Tabla subfield
CREATE TABLE IF NOT EXISTS subfield (
    id SERIAL PRIMARY KEY,
    alias TEXT NOT NULL,
    field_id INTEGER NOT NULL REFERENCES field(id),
    weight NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(alias, field_id)
);

-- Tabla paper (adaptada para OpenAlex)
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,  -- Cambiado de JSONB a TEXT para compatibilidad
    year INTEGER,
    abstract TEXT,
    url TEXT,
    pdf_url TEXT,
    scholar_url TEXT,
    venue TEXT,
    keywords TEXT,  -- Cambiado de JSONB a TEXT para compatibilidad
    citations INTEGER DEFAULT 0,
    title_hash TEXT,
    doi TEXT,
    arxiv_id TEXT,
    s2_fields JSONB,
    area TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla paper_concept
CREATE TABLE IF NOT EXISTS paper_concept (
    id BIGSERIAL PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(paper_id),
    concept TEXT NOT NULL,
    score NUMERIC,
    UNIQUE(paper_id, concept)
);

-- Tabla paper_taxonomy
CREATE TABLE IF NOT EXISTS paper_taxonomy (
    id BIGSERIAL PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(paper_id),
    area_id TEXT NOT NULL REFERENCES area(id),
    field_id INTEGER REFERENCES field(id),
    subfield_id INTEGER REFERENCES subfield(id),
    confidence NUMERIC,
    UNIQUE(paper_id, area_id, field_id, subfield_id)
);

-- Tabla para logs de extracción
CREATE TABLE IF NOT EXISTS extraction_logs (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    papers_found INTEGER DEFAULT 0,
    papers_new INTEGER DEFAULT 0,
    papers_updated INTEGER DEFAULT 0,
    extraction_mode TEXT,
    proxy_used TEXT,
    duration_seconds NUMERIC,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla para checkpoints de extracción
CREATE TABLE IF NOT EXISTS extraction_checkpoints (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    cursor TEXT,
    papers_processed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_papers_citations ON papers (citations DESC);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers (year);
CREATE INDEX IF NOT EXISTS idx_papers_created_at ON papers (created_at);
CREATE INDEX IF NOT EXISTS idx_papers_title_hash ON papers (title_hash);
CREATE INDEX IF NOT EXISTS idx_field_area_id ON field (area_id);
CREATE INDEX IF NOT EXISTS idx_subfield_field_id ON subfield (field_id);
CREATE INDEX IF NOT EXISTS idx_paper_concept_paper_id ON paper_concept (paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_taxonomy_paper_id ON paper_taxonomy (paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_taxonomy_area_id ON paper_taxonomy (area_id);

-- Comentarios para documentación
COMMENT ON TABLE area IS 'Áreas principales de investigación en AI Safety';
COMMENT ON TABLE field IS 'Campos de investigación (Primary y Secondary)';
COMMENT ON TABLE subfield IS 'Subcampos específicos con alias';
COMMENT ON TABLE papers IS 'Papers extraídos de OpenAlex';
COMMENT ON TABLE paper_concept IS 'Conceptos semánticos asociados a papers';
COMMENT ON TABLE paper_taxonomy IS 'Mapeo de papers a taxonomía de investigación';
