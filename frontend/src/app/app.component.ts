import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterOutlet } from '@angular/router';

import { environment } from '../environments/environment';
import { AuthService } from './core/auth.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  readonly env = environment;
  private readonly auth = inject(AuthService);

  tokenDraft = '';

  constructor() {
    this.tokenDraft = this.auth.getToken() ?? '';
  }

  persistToken(): void {
    const t = this.tokenDraft.trim();
    if (t) this.auth.setToken(t);
    else this.auth.clearToken();
  }
}
