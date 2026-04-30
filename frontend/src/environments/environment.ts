/** Local `ng serve`: same-origin `/api` is proxied to the FastAPI backend (see `proxy.conf.json`). */
export const environment = {
  production: false,
  apiUrl: '/api/v1',
  /** Show banner to paste a Bearer token (only if API uses JWT; backend defaults to AUTH_DISABLED) */
  devAuthBanner: false,
  /** Link shown when search has no results (adjust to your ticketing route) */
  ticketSubmitUrl: 'https://support.example.com/tickets/new',
};
