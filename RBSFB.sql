--
-- PostgreSQL database dump
--

-- Dumped from database version 9.5.5
-- Dumped by pg_dump version 9.5.1

-- Started on 2017-02-19 11:18:54

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE "RBSFB";
--
-- TOC entry 2126 (class 1262 OID 59947)
-- Name: RBSFB; Type: DATABASE; Schema: -; Owner: postgres
--

CREATE DATABASE "RBSFB" WITH TEMPLATE = template0 ENCODING = 'UTF8' LC_COLLATE = 'en_US.UTF-8' LC_CTYPE = 'en_US.UTF-8';


ALTER DATABASE "RBSFB" OWNER TO postgres;

\connect "RBSFB"

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 6 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO postgres;

--
-- TOC entry 2127 (class 0 OID 0)
-- Dependencies: 6
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- TOC entry 1 (class 3079 OID 12361)
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- TOC entry 2129 (class 0 OID 0)
-- Dependencies: 1
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 183 (class 1259 OID 60029)
-- Name: TB_EC_LOG; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "TB_EC_LOG" (
    "LOG_ID" integer NOT NULL,
    "TERMINAL_ID" character varying(32),
    "DT_LOG" timestamp without time zone DEFAULT timezone('utc'::text, now()),
    "ST_IP" character varying(45),
    "N_PORT" integer,
    "F_BAD" character varying(1) DEFAULT 'N'::character varying NOT NULL,
    "TX_USER_AGENT" text,
    "ST_BROWSCAP_DATA" text,
    "TX_PATH" text,
    "TX_CONTEXT" text
);


ALTER TABLE "TB_EC_LOG" OWNER TO postgres;

--
-- TOC entry 182 (class 1259 OID 60027)
-- Name: TB_EC_LOG_LOG_ID_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE "TB_EC_LOG_LOG_ID_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "TB_EC_LOG_LOG_ID_seq" OWNER TO postgres;

--
-- TOC entry 2130 (class 0 OID 0)
-- Dependencies: 182
-- Name: TB_EC_LOG_LOG_ID_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE "TB_EC_LOG_LOG_ID_seq" OWNED BY "TB_EC_LOG"."LOG_ID";


--
-- TOC entry 184 (class 1259 OID 60061)
-- Name: TB_EC_MSG; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "TB_EC_MSG" (
    "MSG_ID" integer DEFAULT nextval('"TB_EC_LOG_LOG_ID_seq"'::regclass) NOT NULL,
    "DT_MSG" timestamp without time zone DEFAULT timezone('utc'::text, now()),
    "ST_NAME" character varying(40),
    "ST_LEVEL" character varying(10),
    "ST_MODULE" character varying(40),
    "ST_FILENAME" text,
    "ST_FUNCTION" character varying(50),
    "N_LINE" integer,
    "TX_MSG" text
);


ALTER TABLE "TB_EC_MSG" OWNER TO postgres;


CREATE SEQUENCE "TB_EC_DEBUG_ID_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "TB_EC_DEBUG_ID_seq" OWNER TO postgres;

CREATE TABLE "TB_EC_DEBUG" (
    "DEBUG_ID" integer DEFAULT nextval('"TB_EC_DEBUG_ID_seq"'::regclass) NOT NULL,
    "DT_CRE" timestamp without time zone DEFAULT timezone('utc'::text, now()),
    "ST_NAME" character varying(40),
    "ST_LEVEL" character varying(10),
    "ST_MODULE" character varying(40),
    "ST_FILENAME" text,
    "ST_FUNCTION" character varying(50),
    "N_LINE" integer,
    "TX_MSG" text
);

ALTER TABLE "TB_EC_DEBUG" OWNER TO postgres;

ALTER TABLE ONLY "TB_EC_DEBUG"
    ADD CONSTRAINT "TB_EC_DEBUG_pkey" PRIMARY KEY ("DEBUG_ID");

--
-- TOC entry 1997 (class 2604 OID 60032)
-- Name: LOG_ID; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "TB_EC_LOG" ALTER COLUMN "LOG_ID" SET DEFAULT nextval('"TB_EC_LOG_LOG_ID_seq"'::regclass);


--
-- TOC entry 2005 (class 2606 OID 60039)
-- Name: TB_EC_LOG_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "TB_EC_LOG"
    ADD CONSTRAINT "TB_EC_LOG_pkey" PRIMARY KEY ("LOG_ID");


--
-- TOC entry 2007 (class 2606 OID 60070)
-- Name: TB_EC_MSG_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "TB_EC_MSG"
    ADD CONSTRAINT "TB_EC_MSG_pkey" PRIMARY KEY ("MSG_ID");


--
-- TOC entry 2128 (class 0 OID 0)
-- Dependencies: 6
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2017-02-19 11:18:54

--
-- PostgreSQL database dump complete
--

