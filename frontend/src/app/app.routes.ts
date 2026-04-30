import { Routes } from '@angular/router';

import { kbEditorGuard } from './core/kb-editor.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'kb', pathMatch: 'full' },
  {
    path: 'kb',
    loadComponent: () =>
      import('./kb/kb-portal/kb-portal.component').then((m) => m.KbPortalComponent),
  },
  {
    path: 'kb/article/:articleId',
    loadComponent: () =>
      import('./kb/kb-portal/kb-portal.component').then((m) => m.KbPortalComponent),
  },
  {
    path: 'kb/editor',
    loadComponent: () =>
      import('./kb/kb-editor/kb-editor.component').then((m) => m.KbEditorComponent),
    canActivate: [kbEditorGuard],
  },
  {
    path: 'kb/chat-demo',
    loadComponent: () =>
      import('./kb/kb-chatbot-demo/kb-chatbot-demo.component').then(
        (m) => m.KbChatbotDemoComponent,
      ),
  },
];
