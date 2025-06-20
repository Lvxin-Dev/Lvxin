--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: account_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.account_type AS ENUM (
    'individual',
    'company_admin'
);


--
-- Name: upload_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.upload_status AS ENUM (
    'in_progress',
    'completed',
    'failed'
);


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.files (
    id integer NOT NULL,
    user_id uuid,
    file_name character varying(255) NOT NULL,
    uploaded_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    analyzed_at timestamp with time zone,
    report_name character varying(255)
);


ALTER TABLE public.files OWNER TO postgres;

--
-- Name: files_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.files_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.files_id_seq OWNER TO postgres;

--
-- Name: files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.files_id_seq OWNED BY public.files.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    password text,
    email text,
    phone text,
    age integer,
    language text,
    country text,
    subscription text,
    full_name text,
    files_names text,
    username text,
    wechat_openid text,
    wechat_unionid text,
    avatar_url text,
    account_type public.account_type DEFAULT 'individual'::public.account_type NOT NULL,
    company_id uuid
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: files id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.files ALTER COLUMN id SET DEFAULT nextval('public.files_id_seq'::regclass);


--
-- Data for Name: files; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.files (id, user_id, file_name, uploaded_at, analyzed_at, report_name) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (user_id, password, email, phone, age, language, country, subscription, full_name, files_names, username, wechat_openid, wechat_unionid, avatar_url) FROM stdin;
d644a682-70ab-42f2-988d-7441a7eb2afb	$2b$12$kmC9a67e5v.BF34AuZrVb.eNyQm2LlOFG.j/2AkXpvnpy12jhvkc.	mohamedali314159@gmail.com	\N	\N	\N	\N	\N	Mohamed Ali	\N	mohamedali314159112	\N	\N	\N
17260175-f9e4-47a3-ad11-e6d110927592	$2b$12$GB0XAXTbKZmJpJVydLjGUOpT7cn3v5EZbdeVyh6Yu.t3oAtAeZ.iK	mohamedaly6600@yahoo.com		\N	\N	\N	\N	Momo	\N	Momo	\N	\N	\N
\.


--
-- Name: files_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.files_id_seq', 1, false);


--
-- Name: files files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_wechat_openid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_wechat_openid_key UNIQUE (wechat_openid);


--
-- Name: users users_wechat_unionid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_wechat_unionid_key UNIQUE (wechat_unionid);


--
-- Name: file_upload_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.file_upload_sessions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    file_size bigint NOT NULL,
    mime_type character varying(255),
    status public.upload_status DEFAULT 'in_progress' NOT NULL,
    uploaded_size bigint DEFAULT 0 NOT NULL,
    storage_path text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    final_file_id integer
);


ALTER TABLE public.file_upload_sessions OWNER TO postgres;

--
-- Name: file_upload_sessions file_upload_sessions_final_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.file_upload_sessions
    ADD CONSTRAINT file_upload_sessions_final_file_id_fkey FOREIGN KEY (final_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: file_upload_sessions file_upload_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.file_upload_sessions
    ADD CONSTRAINT file_upload_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: files files_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: idx_resumable_uploads; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_resumable_uploads ON public.file_upload_sessions USING btree (user_id, file_name) WHERE (status = 'in_progress'::public.upload_status);


--
-- Name: companies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.companies (
    comp_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    license character varying(255),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.companies OWNER TO postgres;


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (comp_id);


--
-- Name: users users_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(comp_id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

