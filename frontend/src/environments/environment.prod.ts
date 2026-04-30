/** Production / static builds: browser calls API directly (configure real URL for deployment). */
export const environment = {
  production: true,
  apiUrl: 'http://127.0.0.1:8000/api/v1',
  devAuthBanner: false,
  ticketSubmitUrl: 'https://support.example.com/tickets/new',
};
