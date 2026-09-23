# Rails WEBSEC401 fixture: one owner-checked action (clean), one that
# skips the owner check (planted finding).
#
# frob:ticket T-5356
class OrdersController < ApplicationController
  def show
    @order = Order.where(id: params[:id], user_id: current_user.id).first
  end

  def show_unsafe
    @order = Order.where(id: params[:id]).first
  end
end
