import { Component, inject, signal } from '@angular/core';
import { MarkdownComponent } from 'ngx-markdown';
import { KbApiService } from '../../core/kb-api.service';
import { KbSearchComponent } from '../kb-search/kb-search.component';
import type { KbArticle } from '../kb.models';

@Component({
  selector: 'app-kb-chatbot-demo',
  standalone: true,
  imports: [KbSearchComponent, MarkdownComponent],
  templateUrl: './kb-chatbot-demo.component.html',
  styleUrl: './kb-chatbot-demo.component.scss',
})
export class KbChatbotDemoComponent {
  private readonly api = inject(KbApiService);
  readonly article = signal<KbArticle | null>(null);

  onSelectArticle(id: string): void {
    this.api.getArticle(id).subscribe({
      next: (a) => this.article.set(a),
      error: () => this.article.set(null),
    });
  }
}
