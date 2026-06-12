-- category-product-tag-builder Supabase şeması (çok kiracılı: brand_slug)
create table if not exists pools (
  brand_slug text not null,
  category   text not null,
  pool       jsonb not null,
  updated_at timestamptz default now(),
  primary key (brand_slug, category)
);

create table if not exists product_tags (
  brand_slug text not null,
  product_id text not null,
  url        text,
  name       text,
  category   text,
  tags       jsonb,
  updated_at timestamptz default now(),
  primary key (brand_slug, product_id)
);

create table if not exists combos (
  brand_slug text not null,
  combo      text not null,
  volume     integer,
  decision   text,
  parts      jsonb,
  updated_at timestamptz default now(),
  primary key (brand_slug, combo)
);
