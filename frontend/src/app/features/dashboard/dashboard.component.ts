/**
 * Module: features/dashboard/dashboard.component.ts
 * Nhiệm vụ: Màn hình Tổng quan Quản trị Cửa hàng (Admin/Manager Dashboard).
 *           Hiển thị các chỉ số vận hành cửa hàng và điều hướng sang Quản lý Danh mục & Sản phẩm (`/catalog`).
 */

import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService, User } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  activeTab = signal<'today' | 'week' | 'month'>('today');
  chartMetric = signal<'revenue' | 'volume'>('revenue');
  searchQuery = '';

  currentUser = signal<User | null>(null);

  constructor(public authService: AuthService) {}

  ngOnInit(): void {
    const user = this.authService.currentUser();
    if (user) {
      this.currentUser.set(user);
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
