import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, input, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { Subject, of } from 'rxjs';
import {
  catchError,
  debounceTime,
  distinctUntilChanged,
  switchMap,
  tap,
} from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { KbApiService } from '../../core/kb-api.service';
import type { KbSearchHit } from '../kb.models';

@Component({
  selector: 'app-kb-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './kb-search.component.html',
  styleUrl: './kb-search.component.scss',
})
export class KbSearchComponent {
  private readonly api = inject(KbApiService);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly destroyRef = inject(DestroyRef);

  /** portal: navigate via router from parent; chatbot: inline article */
  readonly variant = input<'portal' | 'chatbot'>('portal');

  readonly articleSelected = output<string>();

  readonly ticketSubmitUrl = environment.ticketSubmitUrl;

  query = '';
  loading = false;
  error: string | null = null;
  hits: KbSearchHit[] = [];
  total = 0;
  easterEgg = false;
  searched = false;

  private readonly query$ = new Subject<string>();

  constructor() {
    this.query$
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        tap(() => {
          this.error = null;
          this.easterEgg = false;
        }),
        switchMap((raw) => {
          const q = raw.trim();
          if (!q) {
            this.hits = [];
            this.total = 0;
            this.searched = false;
            return of(null);
          }
          if (/\bfloppy\b/i.test(q)) {
            this.easterEgg = true;
            this.hits = [];
            this.total = 0;
            this.searched = true;
            this.loading = false;
            return of(null);
          }
          this.loading = true;
          this.searched = true;
          return this.api.search(q, { limit: 20 }).pipe(
            catchError((e: Error) => {
              this.error = e.message || 'Search failed';
              this.loading = false;
              return of(null);
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((res) => {
        this.loading = false;
        if (!res) return;
        this.hits = res.data;
        this.total = res.total;
      });
  }

  /** ngModel updates `query`; we only feed the debounced search stream. */
  onQueryChange(value: string): void {
    this.query$.next(value);
  }

  snippetHtml(snippet: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(snippet);
  }

  selectHit(hit: KbSearchHit): void {
    this.articleSelected.emit(hit.article_id);
  }

  trackById(_: number, hit: KbSearchHit): string {
    return hit.article_id;
  }
}
