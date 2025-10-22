-- Schema para AI Safety Papers Database
-- Basado en schema.dbml

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

-- Tabla paper (modificada para incluir source)
CREATE TABLE IF NOT EXISTS paper (
    paper_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,  -- Cambiado de jsonb a text para compatibilidad
    year INTEGER,
    abstract TEXT,
    url TEXT,
    pdf_url TEXT,
    scholar_url TEXT,
    venue TEXT,
    keywords TEXT,  -- Cambiado de jsonb a text para compatibilidad
    citations INTEGER DEFAULT 0,
    title_hash TEXT,
    doi TEXT,
    arxiv_id TEXT,
    s2_fields TEXT,  -- Cambiado de jsonb a text para compatibilidad
    area TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    publication_date DATE,
    source TEXT DEFAULT 'semantic_scholar'  -- Nueva columna para tracking
);

-- Tabla paper_concept
CREATE TABLE IF NOT EXISTS paper_concept (
    id BIGSERIAL PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES paper(paper_id),
    concept TEXT NOT NULL,
    score NUMERIC,
    UNIQUE(paper_id, concept)
);

-- Tabla paper_taxonomy
CREATE TABLE IF NOT EXISTS paper_taxonomy (
    id BIGSERIAL PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES paper(paper_id),
    area_id TEXT NOT NULL REFERENCES area(id),
    field_id INTEGER REFERENCES field(id),
    subfield_id INTEGER REFERENCES subfield(id),
    confidence NUMERIC,
    UNIQUE(paper_id, area_id, field_id, subfield_id)
);

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_paper_year ON paper(year);
CREATE INDEX IF NOT EXISTS idx_paper_citations ON paper(citations);
CREATE INDEX IF NOT EXISTS idx_paper_source ON paper(source);
CREATE INDEX IF NOT EXISTS idx_paper_created_at ON paper(created_at);
CREATE INDEX IF NOT EXISTS idx_field_area_id ON field(area_id);
CREATE INDEX IF NOT EXISTS idx_subfield_field_id ON subfield(field_id);
CREATE INDEX IF NOT EXISTS idx_paper_concept_paper_id ON paper_concept(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_taxonomy_paper_id ON paper_taxonomy(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_taxonomy_area_id ON paper_taxonomy(area_id);
