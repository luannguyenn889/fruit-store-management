/**
 * Module: features/users/users.component.ts
 * Nhiệm vụ: Màn hình Cấu hình, Hồ sơ cá nhân & Quản trị Nhân sự (/users).
 *           Tuân thủ `FRONTEND_DESIGN_RULES.md` và `UI_UX_DESIGN_RULES_FruitStore.md`:
 *           - Tab Quản trị Nhân sự & Phân quyền (ADMIN): tìm kiếm/lọc tài khoản, tạo tài khoản nhân viên
 *             (`MANAGER`, `STAFF`, `WAREHOUSE`, `ADMIN`), cập nhật vai trò và khóa/mở khóa tài khoản có xác nhận.
 *           - Tab Hồ sơ cá nhân & Đổi mật khẩu (mọi tài khoản): cập nhật họ tên/SĐT (`PATCH /auth/me`)
 *             và đổi mật khẩu (`POST /auth/change-password`).
 */

import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  AuthService,
  RoleInfo,
  User,
  UserStatus
} from '../../core/services/auth.service';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.css']
})
export class UsersComponent implements OnInit {
  currentUser = computed(() => this.authService.currentUser());
  isAdmin = computed(() => this.authService.hasRole('ADMIN'));

  // Tab đang hiển thị: 'staff' (Quản trị nhân sự) hoặc 'profile' (Hồ sơ & Đổi mật khẩu)
  activeTab = signal<'staff' | 'profile'>('staff');

  // Thông báo phản hồi sau khi server xác nhận
  toastMessage = signal('');
  toastType = signal<'success' | 'error'>('success');

  // ===========================================================================
  // DỮ LIỆU QUẢN TRỊ NHÂN SỰ (CHỈ ADMIN)
  // ===========================================================================
  roles = signal<RoleInfo[]>([]);
  users = signal<User[]>([]);
  totalUsers = signal(0);
  isLoadingUsers = signal(false);
  usersError = signal('');

  searchQuery = '';
  filterRole = '';
  filterStatus = '';

  // Modal Tạo tài khoản nhân sự
  showCreateModal = signal(false);
  isCreatingUser = signal(false);
  createError = signal('');
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
  rolesModalError = signal('');

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
  profileError = signal('');

  currentPassword = '';
  newPasswordInput = '';
  confirmPasswordInput = '';
  showPasswords = false;
  isSavingPassword = signal(false);
  passwordError = signal('');

  constructor(public authService: AuthService) {}

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
        // Fallback hiển thị bộ 5 vai trò chuẩn nếu chưa tải được danh mục
      }
    });
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoadingUsers.set(true);
    this.usersError.set('');

    this.authService
      .getUsers({
        page: 1,
        size: 50,
        q: this.searchQuery,
        role_code: this.filterRole || undefined,
        status: this.filterStatus || undefined
      })
      .subscribe({
        next: res => {
          this.users.set(res.items);
          this.totalUsers.set(res.total);
          this.isLoadingUsers.set(false);
        },
        error: err => {
          this.isLoadingUsers.set(false);
          this.usersError.set(
            err.error?.message ||
              'Chưa thể tải danh sách nhân sự từ Auth Service (:8001). Vui lòng kiểm tra quyền ADMIN và kết nối backend.'
          );
        }
      });
  }

  resetFilters(): void {
    this.searchQuery = '';
    this.filterRole = '';
    this.filterStatus = '';
    this.loadUsers();
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
    this.createError.set('');
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
    this.createError.set('');
    if (!this.newFullName.trim() || this.newFullName.trim().length < 2) {
      this.createError.set('Họ và tên phải có tối thiểu 2 ký tự.');
      return;
    }
    if (!this.newEmail.trim() || !this.newEmail.includes('@')) {
      this.createError.set('Vui lòng nhập địa chỉ email hợp lệ.');
      return;
    }
    if (!this.newPassword || this.newPassword.length < 6) {
      this.createError.set('Mật khẩu khởi tạo phải có tối thiểu 6 ký tự.');
      return;
    }
    if (this.selectedCreateRoles.size === 0) {
      this.createError.set('Vui lòng chọn ít nhất một vai trò cho tài khoản.');
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
          this.loadUsers();
          this.showToast(
            `Đã tạo tài khoản "${created.full_name}" (${created.email}) thành công.`,
            'success'
          );
        },
        error: err => {
          this.isCreatingUser.set(false);
          this.createError.set(
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
    this.rolesModalError.set('');
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

    this.rolesModalError.set('');
    if (this.selectedEditRoles.size === 0) {
      this.rolesModalError.set('Tài khoản phải có ít nhất một vai trò.');
      return;
    }

    this.isSavingRoles.set(true);
    this.authService
      .updateUserRoles(target.id, Array.from(this.selectedEditRoles))
      .subscribe({
        next: updated => {
          this.isSavingRoles.set(false);
          this.closeRolesModal();
          this.loadUsers();
          this.showToast(
            `Đã cập nhật vai trò cho tài khoản "${updated.full_name}".`,
            'success'
          );
        },
        error: err => {
          this.isSavingRoles.set(false);
          this.rolesModalError.set(
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
        this.loadUsers();
        const label =
          updated.status === 'ACTIVE' ? 'mở khóa (Hoạt động)' : 'khóa tài khoản';
        this.showToast(`Đã ${label} cho "${updated.full_name}".`, 'success');
      },
      error: err => {
        this.isSavingStatus.set(false);
        this.closeStatusModal();
        this.showToast(
          err.error?.message || 'Không thể thay đổi trạng thái tài khoản.',
          'error'
        );
      }
    });
  }

  // ===========================================================================
  // 4. HỒ SƠ CÁ NHÂN & ĐỔI MẬT KHẨU
  // ===========================================================================
  submitProfileUpdate(): void {
    this.profileError.set('');
    if (!this.profileFullName.trim() || this.profileFullName.trim().length < 2) {
      this.profileError.set('Họ và tên phải có tối thiểu 2 ký tự.');
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
          this.showToast('Đã cập nhật thông tin hồ sơ cá nhân thành công.', 'success');
        },
        error: err => {
          this.isSavingProfile.set(false);
          this.profileError.set(
            err.error?.message || 'Không thể cập nhật thông tin cá nhân.'
          );
        }
      });
  }

  submitChangePassword(): void {
    this.passwordError.set('');
    if (!this.currentPassword) {
      this.passwordError.set('Vui lòng nhập mật khẩu hiện tại.');
      return;
    }
    if (!this.newPasswordInput || this.newPasswordInput.length < 6) {
      this.passwordError.set('Mật khẩu mới phải có tối thiểu 6 ký tự.');
      return;
    }
    if (this.newPasswordInput !== this.confirmPasswordInput) {
      this.passwordError.set('Mật khẩu xác nhận không khớp với mật khẩu mới.');
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
          this.showToast(res.message, 'success');
        },
        error: err => {
          this.isSavingPassword.set(false);
          this.passwordError.set(
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

  showToast(message: string, type: 'success' | 'error' = 'success'): void {
    this.toastMessage.set(message);
    this.toastType.set(type);
    setTimeout(() => {
      if (this.toastMessage() === message) {
        this.toastMessage.set('');
      }
    }, 4500);
  }

  logout(): void {
    this.authService.logout();
  }
}
