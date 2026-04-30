import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MarkdownComponent } from 'ngx-markdown';
import { forkJoin } from 'rxjs';
import { KbApiService } from '../../core/kb-api.service';
import type { ArticleStatus, KbArticleAdmin, KbCategory } from '../kb.models';

type StatusTab = 'all' | ArticleStatus;

@Component({
  selector: 'app-kb-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MarkdownComponent],
  templateUrl: './kb-editor.component.html',
  styleUrl: './kb-editor.component.scss',
})
export class KbEditorComponent implements OnInit {
  private readonly api = inject(KbApiService);

  tabs: { id: StatusTab; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'draft', label: 'Draft' },
    { id: 'published', label: 'Published' },
    { id: 'archived', label: 'Archived' },
  ];
  statusTab: StatusTab = 'all';

  categories: KbCategory[] = [];
  rows: KbArticleAdmin[] = [];
  listError: string | null = null;

  selected: KbArticleAdmin | null = null;
  editTitle = '';
  editContent = '';
  editCategoryId: string | null = null;
  saveError: string | null = null;
  saving = false;

  ngOnInit(): void {
    forkJoin({
      categories: this.api.listCategories(),
      page: this.api.listAdminArticles({ limit: 200 }),
    }).subscribe({
      next: ({ categories, page }) => {
        this.categories = categories;
        this.rows = page.data;
      },
      error: () => {
        this.listError = 'Could not load admin article list.';
      },
    });
  }

  selectTab(tab: StatusTab): void {
    this.statusTab = tab;
    this.reloadList();
  }

  reloadList(): void {
    this.listError = null;
    const status = this.statusTab === 'all' ? undefined : this.statusTab;
    this.api.listAdminArticles({ limit: 200, status }).subscribe({
      next: (p) => {
        this.rows = p.data;
        if (this.selected && !this.rows.some((r) => r.id === this.selected!.id)) {
          this.selected = null;
        }
      },
      error: () => {
        this.listError = 'Could not refresh list.';
      },
    });
  }

  selectRow(row: KbArticleAdmin): void {
    this.selected = row;
    this.editTitle = row.title;
    this.editContent = row.content;
    this.editCategoryId = row.category_id;
    this.saveError = null;
  }

  newArticle(): void {
    this.saving = true;
    this.saveError = null;
    this.api
      .createArticle({
        title: 'New draft article',
        content: '# Title\n\nStart writing…',
        category_id: this.categories[0]?.id ?? null,
      })
      .subscribe({
        next: (a) => {
          const adminRow = { ...a, feedback_count: 0, helpful_percent: null };
          this.rows = [adminRow, ...this.rows];
          this.selectRow(adminRow);
          this.saving = false;
        },
        error: () => {
          this.saveError = 'Could not create article.';
          this.saving = false;
        },
      });
  }

  saveEdits(): void {
    if (!this.selected) return;
    this.saving = true;
    this.saveError = null;
    this.api
      .patchArticle(this.selected.id, {
        title: this.editTitle,
        content: this.editContent,
        category_id: this.editCategoryId,
      })
      .subscribe({
        next: (a) => {
          const merged: KbArticleAdmin = {
            ...a,
            feedback_count: this.selected!.feedback_count,
            helpful_percent: this.selected!.helpful_percent,
          };
          this.selected = merged;
          this.rows = this.rows.map((r) => (r.id === merged.id ? merged : r));
          this.saving = false;
        },
        error: () => {
          this.saveError = 'Save failed.';
          this.saving = false;
        },
      });
  }

  setStatus(status: ArticleStatus): void {
    if (!this.selected) return;
    this.saving = true;
    this.saveError = null;
    this.api.patchArticle(this.selected.id, { status }).subscribe({
      next: (a) => {
        const merged: KbArticleAdmin = {
          ...a,
          feedback_count: this.selected!.feedback_count,
          helpful_percent: this.selected!.helpful_percent,
        };
        this.selected = merged;
        this.reloadList();
        this.saving = false;
      },
      error: () => {
        this.saveError = 'Could not update status.';
        this.saving = false;
      },
    });
  }
}
