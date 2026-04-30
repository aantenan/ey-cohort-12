import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { EMPTY, Observable, expand, reduce } from 'rxjs';
import { environment } from '../../environments/environment';
import type {
  ArticleStatus,
  KbArticle,
  KbArticleAdmin,
  KbCategory,
  KbSearchHit,
  Paginated,
} from '../kb/kb.models';

@Injectable({ providedIn: 'root' })
export class KbApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl + '/kb';

  search(
    q: string,
    opts?: { categoryId?: string; limit?: number; offset?: number },
  ): Observable<Paginated<KbSearchHit>> {
    let params = new HttpParams().set('q', q);
    if (opts?.categoryId) params = params.set('category_id', opts.categoryId);
    if (opts?.limit != null) params = params.set('limit', String(opts.limit));
    if (opts?.offset != null) params = params.set('offset', String(opts.offset));
    return this.http.get<Paginated<KbSearchHit>>(`${this.base}/search`, { params });
  }

  listPublishedArticles(opts?: {
    categoryId?: string;
    q?: string;
    offset?: number;
    limit?: number;
  }): Observable<Paginated<KbArticle>> {
    let params = new HttpParams();
    if (opts?.categoryId) params = params.set('category_id', opts.categoryId);
    if (opts?.q) params = params.set('q', opts.q);
    if (opts?.offset != null) params = params.set('offset', String(opts.offset));
    if (opts?.limit != null) params = params.set('limit', String(opts.limit));
    return this.http.get<Paginated<KbArticle>>(`${this.base}/articles`, { params });
  }

  /**
   * Fetches all published articles in pages (API max limit is 100 per request).
   */
  listAllPublishedArticles(pageSize = 100): Observable<KbArticle[]> {
    return this.listPublishedArticles({ limit: pageSize, offset: 0 }).pipe(
      expand((page) => {
        const nextOff = page.offset + page.data.length;
        if (nextOff >= page.total || page.data.length === 0) {
          return EMPTY;
        }
        return this.listPublishedArticles({
          limit: pageSize,
          offset: nextOff,
        });
      }),
      reduce(
        (acc: KbArticle[], page: Paginated<KbArticle>) => acc.concat(page.data),
        [] as KbArticle[],
      ),
    );
  }

  getArticle(id: string): Observable<KbArticle> {
    return this.http.get<KbArticle>(`${this.base}/articles/${id}`);
  }

  listCategories(): Observable<KbCategory[]> {
    return this.http.get<KbCategory[]>(`${this.base}/categories`);
  }

  submitFeedback(articleId: string, wasHelpful: boolean): Observable<{ id: string }> {
    return this.http.post<{ id: string }>(`${this.base}/articles/${articleId}/feedback`, {
      was_helpful: wasHelpful,
    });
  }

  listAdminArticles(opts?: {
    status?: ArticleStatus;
    offset?: number;
    limit?: number;
  }): Observable<Paginated<KbArticleAdmin>> {
    let params = new HttpParams();
    if (opts?.status) params = params.set('status', opts.status);
    if (opts?.offset != null) params = params.set('offset', String(opts.offset));
    if (opts?.limit != null) params = params.set('limit', String(opts.limit));
    return this.http.get<Paginated<KbArticleAdmin>>(`${this.base}/admin/articles`, { params });
  }

  createArticle(body: {
    title: string;
    content: string;
    category_id?: string | null;
  }): Observable<KbArticle> {
    return this.http.post<KbArticle>(`${this.base}/articles`, body);
  }

  patchArticle(
    id: string,
    body: Partial<{
      title: string;
      content: string;
      category_id: string | null;
      status: ArticleStatus;
    }>,
  ): Observable<KbArticle> {
    return this.http.patch<KbArticle>(`${this.base}/articles/${id}`, body);
  }
}
