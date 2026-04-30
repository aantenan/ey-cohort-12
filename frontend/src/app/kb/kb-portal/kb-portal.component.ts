import { HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MarkdownComponent } from 'ngx-markdown';
import { forkJoin } from 'rxjs';
import { environment } from '../../../environments/environment';
import { KbApiService } from '../../core/kb-api.service';
import { KbSearchComponent } from '../kb-search/kb-search.component';
import type { KbArticle, KbCategory } from '../kb.models';

interface CategoryGroup {
  category: KbCategory;
  articles: KbArticle[];
}

function formatKbLoadError(err: unknown): string {
  const base = `Could not load articles from ${environment.apiUrl}.`;
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) {
      return `${base} Network error or CORS blocked — use the same host as the API allows (e.g. open the app at http://localhost:4200 if the API allows it), and ensure the API is running.`;
    }
    const detail =
      typeof err.error === 'object' && err.error && 'detail' in err.error
        ? String((err.error as { detail: unknown }).detail)
        : err.message;
    return `${base} HTTP ${err.status}: ${detail}`;
  }
  return `${base} ${String(err)}`;
}

@Component({
  selector: 'app-kb-portal',
  standalone: true,
  imports: [CommonModule, RouterLink, MarkdownComponent, KbSearchComponent],
  templateUrl: './kb-portal.component.html',
  styleUrl: './kb-portal.component.scss',
})
export class KbPortalComponent implements OnInit {
  private readonly api = inject(KbApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  groups: CategoryGroup[] = [];
  activeArticleId: string | null = null;
  article: KbArticle | null = null;
  loadingArticle = false;
  loadError: string | null = null;
  indexError: string | null = null;
  feedbackThanks = false;

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const id = pm.get('articleId');
      this.activeArticleId = id;
      if (id) {
        this.loadArticle(id);
      } else {
        this.article = null;
        this.loadError = null;
        this.loadingArticle = false;
        this.feedbackThanks = false;
      }
    });
    this.loadIndex();
  }

  onSearchSelect(articleId: string): void {
    void this.router.navigate(['/kb/article', articleId]);
  }

  backToList(): void {
    void this.router.navigate(['/kb']);
  }

  private loadIndex(): void {
    forkJoin({
      categories: this.api.listCategories(),
      articles: this.api.listAllPublishedArticles(100),
    }).subscribe({
      next: ({ categories, articles }) => {
        this.indexError = null;
        const byCat = new Map<string, KbArticle[]>();
        for (const a of articles) {
          const key = a.category_id ?? '';
          if (!byCat.has(key)) byCat.set(key, []);
          byCat.get(key)!.push(a);
        }
        const groups: CategoryGroup[] = [];
        for (const c of categories) {
          const arts = byCat.get(c.id) ?? [];
          if (arts.length) groups.push({ category: c, articles: arts });
        }
        const unc = byCat.get('');
        if (unc?.length) {
          groups.push({
            category: { id: '', name: 'Uncategorized' },
            articles: unc,
          });
        }
        this.groups = groups;
      },
      error: (err: unknown) => {
        this.indexError = formatKbLoadError(err);
      },
    });
  }

  private loadArticle(id: string): void {
    this.loadError = null;
    this.feedbackThanks = false;
    this.loadingArticle = true;
    this.article = null;
    this.api.getArticle(id).subscribe({
      next: (a) => {
        this.article = a;
        this.loadingArticle = false;
      },
      error: () => {
        this.article = null;
        this.loadError = 'Article not found or not accessible.';
        this.loadingArticle = false;
      },
    });
  }

  vote(helpful: boolean): void {
    if (!this.article) return;
    this.api.submitFeedback(this.article.id, helpful).subscribe({
      next: () => {
        this.feedbackThanks = true;
      },
    });
  }
}
