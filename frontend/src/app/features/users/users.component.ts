/**
 * Module: features/users/users.component.ts
 * Nhiệm vụ: Màn hình Cấu hình, Hồ sơ cá nhân & Quản trị Nhân sự (/users).
 *           Bọc trong `AdminLayoutComponent`, dùng `ToastService`, `SkeletonLoaderComponent`
 *           và `PaginationComponent` tuân thủ đầy đủ quy chuẩn UI/UX.
 */

import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  AuthService,
  RoleInfo,
  User,
  UserStatus
} from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { AdminLayoutComponent } from '../../core/layout/admin-layout/admin-layout.component';
import { SkeletonLoaderComponent } from '../../shared/components/skeleton-loader/skeleton-loader.component';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AdminLayoutComponent,
    SkeletonLoaderComponent,
    PaginationComponent
  ],
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.css']
})
export class UsersComponent implements OnInit {
  currentUser = computed(() => this.authService.currentUser());
  isAdmin = computed(() => this.authService.hasRole('ADMIN'));

  // Tab đang hiển thị: 'staff' (Quản trị nhân sự) hoặc 'profile' (Hồ sơ & Đổi mật khẩu)
  activeTab = signal<'staff' | 'profile'>('staff');

  // ===========================================================================
  // DỮ LIỆU QUẢN TRỊ NHÂN SỰ & PHÂN TRANG (CHỈ ADMIN)
  // ===========================================================================
  roles = signal<RoleInfo[]>([]);
  users = signal<User[]>([]);
  totalUsers = signal(0);
  currentPage = signal(1);
  pageSize = signal(20);
  totalPages = signal(1);
  isLoadingUsers = signal(false);
  usersError = signal('');

  searchQuery = '';
  filterRole = '';
  filterStatus = '';

  // Modal Tạo tài khoản nhân sự
  showCreateModal = signal(false);
  isCreatingUser = signal(false);
  newFullName = '';
  newEmail = '';
  newPhone = '';
  newPassword = '';
  selectedCreateRoles = new Set<string>(['STAFF']);

  // Modal Cập nhật vai trò
  showRolesModal = signal(false);
  targetUserForRoles = signal<User | null>(null);
  selectedEditRoles = new Set<string>();
  isSavingRoles = signal(false);

  // Modal Xác nhận Khóa / Mở khóa tài khoản
  showStatusModal = signal(false);
  targetUserForStatus = signal<User | null>(null);
  targetNewStatus = signal<UserStatus>('LOCKED');
  isSavingStatus = signal(false);

  // ===========================================================================
  // HỒ SƠ CÁ NHÂN & ĐỔI MẬT KHẨU
  // ===========================================================================
  profileFullName = '';
  profilePhone = '';
  isSavingProfile = signal(false);

  currentPassword = '';
  newPasswordInput = '';
  confirmPasswordInput = '';
  showPasswords = false;
  isSavingPassword = signal(false);

  constructor(
    public authService: AuthService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.syncProfileForm();
    if (this.isAdmin()) {
      this.activeTab.set('staff');
      this.loadRolesAndUsers();
    } else {
      this.activeTab.set('profile');
    }
  }

  setTab(tab: 'staff' | 'profile'): void {
    this.activeTab.set(tab);
    if (tab === 'staff' && this.isAdmin() && this.users().length === 0) {
      this.loadRolesAndUsers();
    }
    if (tab === 'profile') {
      this.syncProfileForm();
    }
  }

  private syncProfileForm(): void {
    const user = this.currentUser();
    if (user) {
      this.profileFullName = user.full_name || '';
      this.profilePhone = user.phone || '';
    }
  }

  // ===========================================================================
  // 1. TẢI DỮ LIỆU & LỌC DANH SÁCH NHÂN SỰ
  // ===========================================================================
  loadRolesAndUsers(): void {
    this.authService.getRoles().subscribe({
      next: list => this.roles.set(list),
      error: () => {
        // Fallback hiển thị danh mục mặc định nếu chưa tải được
      }
    });
    this.loadUsers(1);
  }

  loadUsers(page = 1): void {
    this.isLoadingUsers.set(true);
    this.usersError.set('');
    this.currentPage.set(page);

    this.authService
      .getUsers({
        page,
        size: this.pageSize(),
        q: this.searchQuery,
        role_code: this.filterRole || undefined,
        status: this.filterStatus || undefined
      })
      .subscribe({
        next: res => {
          this.users.set(res.items);
          this.totalUsers.set(res.total);
          this.totalPages.set(res.pages);
          this.isLoadingUsers.set(false);
        },
        error: err => {
          this.isLoadingUsers.set(false);
          const msg =
            err.error?.message ||
            'Chưa thể tải danh sách nhân sự từ Auth Service (:8001). Vui lòng kiểm tra quyền ADMIN và kết nối backend.';
          this.usersError.set(msg);
          this.toastService.error(msg);
        }
      });
  }

  resetFilters(): void {
    this.searchQuery = '';
    this.filterRole = '';
    this.filterStatus = '';
    this.loadUsers(1);
  }

  // ===========================================================================
  // 2. TẠO TÀI KHOẢN NHÂN SỰ (ADMIN)
  // ===========================================================================
  openCreateUserModal(): void {
    this.newFullName = '';
    this.newEmail = '';
    this.newPhone = '';
    this.newPassword = '';
    this.selectedCreateRoles = new Set<string>(['STAFF']);
    this.showCreateModal.set(true);
  }

  closeCreateUserModal(): void {
    this.showCreateModal.set(false);
  }

  toggleCreateRole(code: string): void {
    if (this.selectedCreateRoles.has(code)) {
      this.selectedCreateRoles.delete(code);
    } else {
      this.selectedCreateRoles.add(code);
    }
  }

  submitCreateUser(): void {
    if (!this.newFullName.trim() || this.newFullName.trim().length < 2) {
      this.toastService.error('Họ và tên phải có tối thiểu 2 ký tự.');
      return;
    }
    if (!this.newEmail.trim() || !this.newEmail.includes('@')) {
      this.toastService.error('Vui lòng nhập địa chỉ email hợp lệ.');
      return;
    }
    if (!this.newPassword || this.newPassword.length < 6) {
      this.toastService.error('Mật khẩu khởi tạo phải có tối thiểu 6 ký tự.');
      return;
    }
    if (this.selectedCreateRoles.size === 0) {
      this.toastService.error('Vui lòng chọn ít nhất một vai trò cho tài khoản.');
      return;
    }

    this.isCreatingUser.set(true);
    this.authService
      .createUser({
        full_name: this.newFullName.trim(),
        email: this.newEmail.trim(),
        phone: this.newPhone.trim() || undefined,
        password: this.newPassword,
        role_codes: Array.from(this.selectedCreateRoles)
      })
      .subscribe({
        next: created => {
          this.isCreatingUser.set(false);
          this.showCreateModal.set(false);
          this.loadUsers(this.currentPage());
          this.toastService.success(
            `Đã tạo tài khoản "${created.full_name}" (${created.email}) thành công.`
          );
        },
        error: err => {
          this.isCreatingUser.set(false);
          this.toastService.error(
            err.error?.message || 'Không thể tạo tài khoản mới. Vui lòng kiểm tra lại.'
          );
        }
      });
  }

  // ===========================================================================
  // 3. CẬP NHẬT VAI TRÒ & KHÓA / MỞ KHÓA TÀI KHOẢN (ADMIN)
  // ===========================================================================
  openRolesModal(user: User): void {
    this.targetUserForRoles.set(user);
    const codes = (user.roles || []).map(r => (typeof r === 'string' ? r : r.code));
    this.selectedEditRoles = new Set<string>(codes);
    this.showRolesModal.set(true);
  }

  closeRolesModal(): void {
    this.showRolesModal.set(false);
    this.targetUserForRoles.set(null);
  }

  toggleEditRole(code: string): void {
    if (this.selectedEditRoles.has(code)) {
      this.selectedEditRoles.delete(code);
    } else {
      this.selectedEditRoles.add(code);
    }
  }

  submitUpdateRoles(): void {
    const target = this.targetUserForRoles();
    if (!target) return;

    if (this.selectedEditRoles.size === 0) {
      this.toastService.error('Tài khoản phải có ít nhất một vai trò.');
      return;
    }

    this.isSavingRoles.set(true);
    this.authService
      .updateUserRoles(target.id, Array.from(this.selectedEditRoles))
      .subscribe({
        next: updated => {
          this.isSavingRoles.set(false);
          this.closeRolesModal();
          this.loadUsers(this.currentPage());
          this.toastService.success(
            `Đã cập nhật vai trò cho tài khoản "${updated.full_name}".`
          );
        },
        error: err => {
          this.isSavingRoles.set(false);
          this.toastService.error(
            err.error?.message || 'Không thể cập nhật vai trò tài khoản.'
          );
        }
      });
  }

  openStatusConfirmModal(user: User, nextStatus: UserStatus): void {
    this.targetUserForStatus.set(user);
    this.targetNewStatus.set(nextStatus);
    this.showStatusModal.set(true);
  }

  closeStatusModal(): void {
    this.showStatusModal.set(false);
    this.targetUserForStatus.set(null);
  }

  confirmStatusChange(): void {
    const target = this.targetUserForStatus();
    if (!target) return;

    this.isSavingStatus.set(true);
    this.authService.updateUserStatus(target.id, this.targetNewStatus()).subscribe({
      next: updated => {
        this.isSavingStatus.set(false);
        this.closeStatusModal();
        this.loadUsers(this.currentPage());
        const label =
          updated.status === 'ACTIVE' ? 'mở khóa (Hoạt động)' : 'khóa tài khoản';
        this.toastService.success(`Đã ${label} cho "${updated.full_name}".`);
      },
      error: err => {
        this.isSavingStatus.set(false);
        this.closeStatusModal();
        this.toastService.error(
          err.error?.message || 'Không thể thay đổi trạng thái tài khoản.'
        );
      }
    });
  }

  // ===========================================================================
  // 4. HỒ SƠ CÁ NHÂN & ĐỔI MẬT KHẨU
  // ===========================================================================
  submitProfileUpdate(): void {
    if (!this.profileFullName.trim() || this.profileFullName.trim().length < 2) {
      this.toastService.error('Họ và tên phải có tối thiểu 2 ký tự.');
      return;
    }

    this.isSavingProfile.set(true);
    this.authService
      .updateProfile({
        full_name: this.profileFullName.trim(),
        phone: this.profilePhone.trim()
      })
      .subscribe({
        next: () => {
          this.isSavingProfile.set(false);
          this.toastService.success('Đã cập nhật thông tin hồ sơ cá nhân thành công.');
        },
        error: err => {
          this.isSavingProfile.set(false);
          this.toastService.error(
            err.error?.message || 'Không thể cập nhật thông tin cá nhân.'
          );
        }
      });
  }

  submitChangePassword(): void {
    if (!this.currentPassword) {
      this.toastService.error('Vui lòng nhập mật khẩu hiện tại.');
      return;
    }
    if (!this.newPasswordInput || this.newPasswordInput.length < 6) {
      this.toastService.error('Mật khẩu mới phải có tối thiểu 6 ký tự.');
      return;
    }
    if (this.newPasswordInput !== this.confirmPasswordInput) {
      this.toastService.error('Mật khẩu xác nhận không khớp với mật khẩu mới.');
      return;
    }

    this.isSavingPassword.set(true);
    this.authService
      .changePassword({
        current_password: this.currentPassword,
        new_password: this.newPasswordInput
      })
      .subscribe({
        next: res => {
          this.isSavingPassword.set(false);
          this.currentPassword = '';
          this.newPasswordInput = '';
          this.confirmPasswordInput = '';
          this.toastService.success(res.message);
        },
        error: err => {
          this.isSavingPassword.set(false);
          this.toastService.error(
            err.error?.message || 'Đổi mật khẩu không thành công. Vui lòng kiểm tra lại.'
          );
        }
      });
  }

  // ===========================================================================
  // TIỆN ÍCH HIỂN THỊ
  // ===========================================================================
  getRoleLabel(role: RoleInfo | string): string {
    if (typeof role === 'string') return role;
    return role.name || role.code;
  }

  getRoleCode(role: RoleInfo | string): string {
    return typeof role === 'string' ? role : role.code;
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'ACTIVE':
        return 'Đang hoạt động';
      case 'LOCKED':
        return 'Đã khóa';
      case 'INACTIVE':
        return 'Ngừng kích hoạt';
      default:
        return status;
    }
  }
}
