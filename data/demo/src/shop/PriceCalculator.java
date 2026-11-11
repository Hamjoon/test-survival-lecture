package shop;
public class PriceCalculator {
    private final DiscountService discounts;
    public PriceCalculator(DiscountService discounts) { this.discounts = discounts; }
    public int finalPrice(String customer, int price) {
        if (price < 0) {
            throw new IllegalArgumentException("negative price");
        }
        int pct = discounts.percentFor(customer);
        return price - price * pct / 100;
    }
}
