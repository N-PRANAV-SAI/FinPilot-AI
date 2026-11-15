import {
  User,
  Quote,
  IndexData,
  PortfolioSummary,
  Order,
  Transaction,
  SearchResult,
  Candle,
  CompanyFundamentals,
  NewsItem,
  FilingItem,
  Lesson,
  AnalysisResult,
} from '../types';

const API_BASE = '/api';

export const api = {
  // Auth & Onboarding
  async register(name: string, email: string, password: string): Promise<{ success: boolean; token?: string; user?: User; error?: string }> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    return res.json();
  },

  async login(email: string, password: string): Promise<{ success: boolean; token?: string; user?: User; error?: string }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return res.json();
  },

  async saveOnboarding(data: {
    user_id: number;
    experience_level: string;
    learning_goals: string[];
    risk_comfort: string;
    preferred_currency: string;
    practice_balance: number;
    trading_mode: string;
  }): Promise<{ success: boolean; message?: string }> {
    const res = await fetch(`${API_BASE}/auth/onboarding`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async getUser(userId: number): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/user/${userId}`);
    return res.json();
  },

  // Market & Quotes
  async getIndices(): Promise<IndexData[]> {
    const res = await fetch(`${API_BASE}/market/indices`);
    const data = await res.json();
    return data.indices || [];
  },

  async searchCompanies(query: string, country?: string): Promise<SearchResult[]> {
    const url = new URL(`${API_BASE}/market/search`, window.location.origin);
    url.searchParams.set('query', query);
    if (country) url.searchParams.set('country', country);
    const res = await fetch(url.toString());
    const data = await res.json();
    return data.results || [];
  },

  async getQuote(ticker: string): Promise<Quote> {
    const res = await fetch(`${API_BASE}/market/quote/${ticker}`);
    return res.json();
  },

  async getCompanyDetails(ticker: string): Promise<{
    ticker: string;
    company_name: string;
    quote: Quote;
    fundamentals: CompanyFundamentals;
    news: NewsItem[];
    filings: FilingItem[];
  }> {
    const res = await fetch(`${API_BASE}/market/company/${ticker}`);
    return res.json();
  },

  async getMarketHistory(ticker: string, period = '1y'): Promise<{ ticker: string; period: string; candles: Candle[] }> {
    const res = await fetch(`${API_BASE}/market/history/${ticker}?period=${period}`);
    return res.json();
  },

  async getAnalysis(ticker: string): Promise<AnalysisResult> {
    const res = await fetch(`${API_BASE}/market/analysis/${ticker}`);
    return res.json();
  },

  // Portfolio & Paper Trading
  async getPortfolio(userId: number): Promise<PortfolioSummary> {
    const res = await fetch(`${API_BASE}/portfolio/${userId}`);
    return res.json();
  },

  async executeBuy(order: {
    user_id: number;
    ticker: string;
    company_name: string;
    exchange: string;
    country: string;
    currency: string;
    order_type?: string;
    quantity?: number;
    investment_amount_acc?: number;
    limit_price?: number;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/trading/buy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(order),
    });
    return res.json();
  },

  async executeSell(order: { user_id: number; ticker: string; quantity: number }): Promise<any> {
    const res = await fetch(`${API_BASE}/trading/sell`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(order),
    });
    return res.json();
  },

  async resetAccount(userId: number, newBalance?: number): Promise<any> {
    const res = await fetch(`${API_BASE}/trading/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, new_balance: newBalance }),
    });
    return res.json();
  },

  async depositFunds(userId: number, amount: number): Promise<any> {
    const res = await fetch(`${API_BASE}/trading/deposit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, amount }),
    });
    return res.json();
  },

  async getOrders(userId: number): Promise<Order[]> {
    const res = await fetch(`${API_BASE}/trading/orders/${userId}`);
    return res.json();
  },

  async getTransactions(userId: number): Promise<Transaction[]> {
    const res = await fetch(`${API_BASE}/trading/transactions/${userId}`);
    return res.json();
  },

  // Watchlist
  async getWatchlist(userId: number): Promise<any[]> {
    const res = await fetch(`${API_BASE}/watchlist/${userId}`);
    const data = await res.json();
    return data.watchlist || [];
  },

  async addToWatchlist(item: { user_id: number; ticker: string; company_name?: string; exchange?: string; country?: string; currency?: string }): Promise<any> {
    const res = await fetch(`${API_BASE}/watchlist/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item),
    });
    return res.json();
  },

  async removeFromWatchlist(userId: number, ticker: string): Promise<any> {
    const res = await fetch(`${API_BASE}/watchlist/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ticker }),
    });
    return res.json();
  },

  // AI Assistant
  async sendChatMessage(userId: number, message: string, ticker?: string, portfolioContext?: any): Promise<{ reply: string }> {
    const res = await fetch(`${API_BASE}/assistant/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        message,
        ticker,
        portfolio_context: portfolioContext,
      }),
    });
    return res.json();
  },

  // Learning
  async getLessons(userId: number): Promise<Lesson[]> {
    const res = await fetch(`${API_BASE}/education/lessons/${userId}`);
    const data = await res.json();
    return data.lessons || [];
  },

  async submitQuiz(userId: number, lessonId: string, selectedOptionIndex: number): Promise<any> {
    const res = await fetch(`${API_BASE}/education/quiz`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        lesson_id: lessonId,
        selected_option_index: selectedOptionIndex,
      }),
    });
    return res.json();
  },

  // AI Profit Predictor & Goal Simulators
  async predictForecast(data: {
    ticker: string;
    investment_amount: number;
    duration?: string | number;
    target_amount?: number;
    risk_level?: string;
    account_currency?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/forecast/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async simulateGoal(data: {
    starting_capital: number;
    target_amount: number;
    time_available?: string | number;
    currency?: string;
    ticker?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/forecast/goal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async simulatePortfolio(data: {
    allocations: Array<{ ticker: string; amount: number }>;
    total_capital?: number;
    duration?: string | number;
    account_currency?: string;
    risk_level?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/forecast/portfolio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },
};
