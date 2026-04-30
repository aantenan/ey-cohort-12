export type ArticleStatus = 'draft' | 'published' | 'archived';

export interface Paginated<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface KbCategory {
  id: string;
  name: string;
}

export interface KbArticle {
  id: string;
  title: string;
  content: string;
  category_id: string | null;
  author_id: string;
  status: ArticleStatus;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface KbArticleAdmin extends KbArticle {
  feedback_count: number;
  helpful_percent: number | null;
}

export interface KbSearchHit {
  article_id: string;
  title: string;
  snippet: string;
  category: string | null;
  published_at: string | null;
  rank: number;
}
