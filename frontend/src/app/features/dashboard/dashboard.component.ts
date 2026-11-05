import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService, User } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  activeTab = signal<'today' | 'week' | 'month'>('today');
  chartMetric = signal<'revenue' | 'volume'>('revenue');
  searchQuery = '';

  currentUser = signal<User | null>(null);

  constructor(private authService: AuthService) {}

  ngOnInit(): void {
    const user = this.authService.currentUser();
    if (user) {
      this.currentUser.set(user);
    } else {
      // Fallback demo user
      this.currentUser.set({
        id: 'demo-id',
        email: 'admin@fruitstore.com',
        full_name: 'Nguyễn Thùy Mai',
        status: 'ACTIVE',
        roles: ['Quản lý Cửa hàng']
      });
    }
  }

  setTab(tab: 'today' | 'week' | 'month'): void {
    this.activeTab.set(tab);
  }

  setChartMetric(metric: 'revenue' | 'volume'): void {
    this.chartMetric.set(metric);
  }

  logout(): void {
    this.authService.logout();
  }
}
