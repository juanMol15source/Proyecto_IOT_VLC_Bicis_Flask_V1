CREATE TABLE IF NOT EXISTS estaciones (
    id        SERIAL PRIMARY KEY,
    nombre    TEXT UNIQUE NOT NULL,
    latitud   DOUBLE PRECISION,
    longitud  DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS mediciones (
    id             BIGSERIAL PRIMARY KEY,
    estacion_id    INTEGER NOT NULL REFERENCES estaciones(id),
    momento        TIMESTAMPTZ NOT NULL,
    bicis_libres   INTEGER,
    huecos_libres  INTEGER,
    UNIQUE (estacion_id, momento)
);
CREATE INDEX IF NOT EXISTS idx_mediciones_momento ON mediciones (momento);

CREATE TABLE IF NOT EXISTS sincronizaciones (
    id                 SERIAL PRIMARY KEY,
    ejecutado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    filas_leidas       INTEGER NOT NULL,
    filas_insertadas   INTEGER NOT NULL
);
